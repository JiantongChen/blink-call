#!/usr/bin/env python3
"""Run only the HRNet ONNX facial-landmark stage used by blink-call.

This diagnostic script deliberately skips YOLO, tracking, eye selection, the
eye-state classifier, and the UI.  It has two input modes:

1. Pass ``--bbox x1 y1 x2 y2`` to reproduce blink-call's HRNet crop and decode
   path for a known (preferably unclipped) YOLO face box.
2. Omit ``--bbox`` when ``--image`` is already the exact face crop.  The image
   is resized directly to the ONNX input size with no additional 1.25 expansion.

Besides annotated images, the script always saves the exact normalized input
tensor and every raw ONNX output.  Those arrays are the reliable way to compare
an ONNX run with a PyTorch .pth run: compare input_tensor first, heatmap second,
and decoded landmarks only after those two match.
"""

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import cv2
import numpy as np


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from blink_call.algorithm.inference.hrnet_onnx import HRNetONNX  # noqa: E402


DEFAULT_ONNX_PATH = (
    Path.home()
    / "Library"
    / "Application Support"
    / "blink_call"
    / "blink_call_model_files"
    / "hrnet"
    / "hrnet.onnx"
)

# WFLW-98 groups, expressed as [start, end) and OpenCV BGR colors.
LANDMARK_GROUPS = (
    (0, 33, (0, 255, 255)),
    (33, 51, (255, 0, 255)),
    (51, 60, (255, 255, 0)),
    (60, 76, (0, 255, 0)),
    (76, 88, (0, 128, 255)),
    (88, 96, (0, 0, 255)),
    (96, 98, (0, 0, 255)),
)

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def parse_args():
    parser = argparse.ArgumentParser(
        description="Pure HRNet WFLW-98 ONNX inference for blink-call diagnostics."
    )
    parser.add_argument(
        "--image",
        required=True,
        type=Path,
        help="Input image path or a directory containing images.",
    )
    parser.add_argument(
        "--onnx",
        "--model",
        dest="onnx_path",
        type=Path,
        default=DEFAULT_ONNX_PATH,
        help=f"HRNet ONNX path (default: {DEFAULT_ONNX_PATH}).",
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("X1", "Y1", "X2", "Y2"),
        help=(
            "Face box in source-image pixels. When supplied, the script uses "
            "the same center/scale crop as blink-call. Use the unclipped YOLO "
            "box for a strict online comparison."
        ),
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        help=(
            "Output directory. For one image the default is IMAGE_stem_hrnet_onnx; "
            "for a directory it is DIRECTORY_name_hrnet_onnx next to that directory."
        ),
    )
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="When --image is a directory, also process images in subdirectories.",
    )
    parser.add_argument(
        "--input-size",
        type=int,
        nargs=2,
        default=(256, 256),
        metavar=("WIDTH", "HEIGHT"),
        help="Model input size; blink-call and the current model use 256 256.",
    )
    parser.add_argument(
        "--expand-ratio",
        type=float,
        default=1.25,
        help="Face-box expansion used only with --bbox (default: 1.25).",
    )
    parser.add_argument(
        "--decode",
        choices=("app", "heatmap", "coords"),
        default="app",
        help=(
            "app: current blink-call behavior (prefer heatmap); heatmap: require "
            "offline-style heatmap decode; coords: use exported ONNX coords."
        ),
    )
    parser.add_argument(
        "--ctx-id",
        type=int,
        default=-1,
        help="-1 forces CPU like the current app configuration; >=0 permits CUDA.",
    )
    parser.add_argument(
        "--draw-indices",
        action="store_true",
        help="Draw WFLW landmark indices next to the points.",
    )
    parser.add_argument(
        "--reference-input",
        type=Path,
        help="Optional offline .npy input tensor for numerical comparison.",
    )
    parser.add_argument(
        "--reference-heatmap",
        type=Path,
        help="Optional offline .npy heatmap for numerical comparison.",
    )
    parser.add_argument(
        "--reference-landmarks",
        type=Path,
        help="Optional offline .npy final landmarks for numerical comparison.",
    )
    return parser.parse_args()


def read_image(path):
    data = np.fromfile(str(path), dtype=np.uint8)
    image = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if image is None:
        raise RuntimeError(f"Could not read image: {path}")
    return image


def write_image(path, image):
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix or ".png"
    ok, encoded = cv2.imencode(suffix, image)
    if not ok:
        raise RuntimeError(f"Could not encode output image: {path}")
    encoded.tofile(str(path))


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def output_metadata(items):
    return [
        {"name": item.name, "shape": list(item.shape), "type": item.type}
        for item in items
    ]


def find_raw_outputs(output_names, outputs):
    """Find heatmap/coords/scores without changing their raw values."""
    heatmap = None
    coords = None
    scores = None

    for name, output in zip(output_names, outputs):
        lowered = name.lower()
        if "heatmap" in lowered:
            heatmap = output
        elif "coord" in lowered:
            coords = output
        elif "score" in lowered or "conf" in lowered:
            scores = output

    for output in outputs:
        if heatmap is None and output.ndim == 4:
            heatmap = output
        elif coords is None and output.ndim in (2, 3) and output.shape[-1] == 2:
            coords = output
        elif scores is None and output.ndim in (1, 2) and output.shape[-1] != 2:
            scores = output

    return heatmap, coords, scores


def squeeze_coords(coords):
    if coords is None:
        return None
    coords = np.asarray(coords)
    if coords.ndim == 3 and coords.shape[0] == 1:
        coords = coords[0]
    if coords.ndim != 2 or coords.shape[-1] != 2:
        raise RuntimeError(f"Unexpected coords output shape: {coords.shape}")
    return coords.astype(np.float32)


def squeeze_scores(scores):
    if scores is None:
        return None
    scores = np.asarray(scores)
    if scores.ndim == 2 and scores.shape[0] == 1:
        scores = scores[0]
    return scores.reshape(-1).astype(np.float32)


def heatmap_coords_to_input(landmarker, coords, heatmap_size, input_size):
    input_w, input_h = input_size
    if input_w != input_h:
        raise RuntimeError("Offline-style HRNet heatmap mapping expects a square input.")
    center = np.array([0.5 * input_w, 0.5 * input_h], dtype=np.float32)
    scale = float(input_w) / 200.0
    return landmarker._transform_preds_to_image(coords, center, scale, heatmap_size)


def map_input_coords_to_direct_image(coords, input_size, image_shape, one_based):
    input_w, input_h = input_size
    image_h, image_w = image_shape[:2]
    mapped = np.asarray(coords, dtype=np.float32).copy()

    if one_based:
        mapped[:, 0] = (mapped[:, 0] - 1.0) * (image_w - 1) / max(input_w - 1, 1) + 1.0
        mapped[:, 1] = (mapped[:, 1] - 1.0) * (image_h - 1) / max(input_h - 1, 1) + 1.0
    else:
        mapped[:, 0] *= (image_w - 1) / max(input_w - 1, 1)
        mapped[:, 1] *= (image_h - 1) / max(input_h - 1, 1)
    return mapped


def map_raw_coords_to_bbox(coords, crop_info, input_size):
    input_w, input_h = input_size
    x1, y1, x2, y2 = crop_info["virtual_box"]
    mapped = np.asarray(coords, dtype=np.float32).copy()
    mapped[:, 0] = mapped[:, 0] * max(1, x2 - x1) / max(input_w - 1, 1) + x1
    mapped[:, 1] = mapped[:, 1] * max(1, y2 - y1) / max(input_h - 1, 1) + y1
    return mapped


def color_for_landmark(index):
    for start, end, color in LANDMARK_GROUPS:
        if start <= index < end:
            return color
    return 255, 255, 255


def draw_landmarks(image, landmarks, draw_indices=False):
    canvas = image.copy()
    diamond_half_size = max(2, int(round(min(canvas.shape[:2]) / 140.0)))
    for index, point in enumerate(np.asarray(landmarks)):
        if not np.all(np.isfinite(point)):
            continue
        x, y = int(round(float(point[0]))), int(round(float(point[1])))
        color = color_for_landmark(index)
        diamond = np.array(
            [
                [x, y - diamond_half_size],
                [x + diamond_half_size, y],
                [x, y + diamond_half_size],
                [x - diamond_half_size, y],
            ],
            dtype=np.int32,
        )
        cv2.fillConvexPoly(canvas, diamond, color, lineType=cv2.LINE_AA)
        if draw_indices:
            cv2.putText(
                canvas,
                str(index),
                (x + 2, y - 2),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.28,
                color,
                1,
                cv2.LINE_AA,
            )
    return canvas


def load_reference(path):
    loaded = np.load(path, allow_pickle=False)
    if isinstance(loaded, np.lib.npyio.NpzFile):
        if len(loaded.files) != 1:
            keys = ", ".join(loaded.files)
            loaded.close()
            raise RuntimeError(
                f"Reference NPZ must contain exactly one array; found: {keys}"
            )
        array = loaded[loaded.files[0]].copy()
        loaded.close()
        return array
    return np.asarray(loaded)


def compare_arrays(actual, reference_path, kind):
    reference = load_reference(reference_path)
    actual = np.asarray(actual)

    if kind == "landmarks":
        if actual.ndim == 3 and actual.shape[0] == 1:
            actual = actual[0]
        if reference.ndim == 3 and reference.shape[0] == 1:
            reference = reference[0]

    result = {
        "reference_path": str(reference_path.resolve()),
        "actual_shape": list(actual.shape),
        "reference_shape": list(reference.shape),
    }
    if actual.shape != reference.shape:
        result["shape_match"] = False
        return result

    result["shape_match"] = True
    difference = actual.astype(np.float64) - reference.astype(np.float64)
    absolute = np.abs(difference)
    result.update(
        {
            "mean_abs": float(np.mean(absolute)),
            "max_abs": float(np.max(absolute)),
            "rmse": float(np.sqrt(np.mean(np.square(difference)))),
            "allclose_atol_1e-4": bool(np.allclose(actual, reference, rtol=0.0, atol=1e-4)),
            "allclose_atol_1e-3": bool(np.allclose(actual, reference, rtol=0.0, atol=1e-3)),
        }
    )

    heatmap = actual[0] if actual.ndim == 4 and actual.shape[0] == 1 else actual
    reference_heatmap = (
        reference[0] if reference.ndim == 4 and reference.shape[0] == 1 else reference
    )
    if kind == "heatmap" and heatmap.ndim == 3:
        actual_argmax = np.argmax(heatmap.reshape(heatmap.shape[0], -1), axis=1)
        reference_argmax = np.argmax(
            reference_heatmap.reshape(reference_heatmap.shape[0], -1), axis=1
        )
        result["landmark_argmax_match_ratio"] = float(
            np.mean(actual_argmax == reference_argmax)
        )

    if kind == "landmarks" and actual.ndim == 2 and actual.shape[-1] == 2:
        distance = np.linalg.norm(difference, axis=1)
        result.update(
            {
                "mean_point_distance_px": float(np.mean(distance)),
                "p95_point_distance_px": float(np.percentile(distance, 95)),
                "max_point_distance_px": float(np.max(distance)),
            }
        )
    return result


def json_ready(value):
    if isinstance(value, np.ndarray):
        return value.tolist()
    if isinstance(value, (np.floating, np.integer)):
        return value.item()
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [json_ready(item) for item in value]
    return value


def infer_one(args, image_path, output_dir, landmarker, model_sha256):
    output_dir.mkdir(parents=True, exist_ok=True)

    input_size = tuple(args.input_size)
    image = read_image(image_path)

    if args.bbox is not None:
        mode = "app_bbox"
        face_crop, crop_info = landmarker._crop_face(image, args.bbox)
        if face_crop is None:
            raise RuntimeError(f"Invalid or out-of-frame face bbox: {args.bbox}")
    else:
        mode = "pre_cropped"
        face_crop = image.copy()
        crop_info = None

    input_w, input_h = input_size
    model_input_bgr = cv2.resize(face_crop, (input_w, input_h))
    input_tensor = landmarker._preprocess(face_crop)

    started_at = time.perf_counter()
    outputs = landmarker.session.run(
        landmarker.output_names,
        {landmarker.input_name: input_tensor},
    )
    inference_ms = (time.perf_counter() - started_at) * 1000.0

    raw_heatmap, raw_coords_value, raw_scores_value = find_raw_outputs(
        landmarker.output_names, outputs
    )
    raw_coords = squeeze_coords(raw_coords_value)
    raw_scores = squeeze_scores(raw_scores_value)

    heatmap_coords = None
    heatmap_scores = None
    heatmap_size = None
    heatmap_input_coords = None
    heatmap_source_coords = None
    if raw_heatmap is not None:
        heatmap_coords, heatmap_scores, heatmap_size = (
            landmarker._decode_heatmap_to_coords_and_scores(raw_heatmap)
        )
        heatmap_input_coords = heatmap_coords_to_input(
            landmarker, heatmap_coords, heatmap_size, input_size
        )
        if crop_info is not None:
            heatmap_source_coords = landmarker._transform_preds_to_image(
                heatmap_coords,
                crop_info["center"],
                crop_info["scale"],
                heatmap_size,
            )
        else:
            heatmap_source_coords = map_input_coords_to_direct_image(
                heatmap_input_coords, input_size, image.shape, one_based=True
            )

    raw_source_coords = None
    if raw_coords is not None:
        if crop_info is not None:
            raw_source_coords = map_raw_coords_to_bbox(raw_coords, crop_info, input_size)
        else:
            raw_source_coords = map_input_coords_to_direct_image(
                raw_coords, input_size, image.shape, one_based=False
            )

    if args.decode == "heatmap":
        if heatmap_source_coords is None:
            raise RuntimeError("--decode heatmap requested, but the ONNX has no heatmap output.")
        selected_space = "heatmap_offline_style"
        selected_source_coords = heatmap_source_coords
        selected_input_coords = heatmap_input_coords
        selected_scores = heatmap_scores
    elif args.decode == "coords":
        if raw_source_coords is None:
            raise RuntimeError("--decode coords requested, but the ONNX has no coords output.")
        selected_space = "onnx_coords_output"
        selected_source_coords = raw_source_coords
        selected_input_coords = raw_coords
        selected_scores = raw_scores
    else:
        # This is exactly the current HRNetONNX preference: heatmap first,
        # coordinate-only output only as a compatibility fallback.
        if heatmap_source_coords is not None:
            selected_space = "app_heatmap_preferred"
            selected_source_coords = heatmap_source_coords
            selected_input_coords = heatmap_input_coords
            selected_scores = heatmap_scores
        elif raw_source_coords is not None:
            selected_space = "app_coords_fallback"
            selected_source_coords = raw_source_coords
            selected_input_coords = raw_coords
            selected_scores = raw_scores
        else:
            shapes = [list(output.shape) for output in outputs]
            raise RuntimeError(f"No supported HRNet output found: {shapes}")

    arrays = {"input_tensor": input_tensor}
    for name, output in zip(landmarker.output_names, outputs):
        safe_name = "".join(char if char.isalnum() or char == "_" else "_" for char in name)
        arrays[f"onnx_{safe_name}"] = output
    optional_arrays = {
        "heatmap_coords_1based": heatmap_coords,
        "heatmap_scores": heatmap_scores,
        "heatmap_landmarks_input": heatmap_input_coords,
        "heatmap_landmarks_source": heatmap_source_coords,
        "onnx_coords_raw": raw_coords,
        "onnx_scores_raw": raw_scores,
        "onnx_coords_landmarks_source": raw_source_coords,
        "selected_landmarks_input": selected_input_coords,
        "selected_landmarks_source": selected_source_coords,
        "selected_scores": selected_scores,
    }
    arrays.update({key: value for key, value in optional_arrays.items() if value is not None})

    arrays_path = output_dir / "debug_arrays.npz"
    np.savez_compressed(arrays_path, **arrays)
    write_image(output_dir / "face_crop.png", face_crop)
    write_image(output_dir / "model_input.png", model_input_bgr)
    write_image(
        output_dir / "model_input_annotated.png",
        draw_landmarks(model_input_bgr, selected_input_coords, args.draw_indices),
    )
    write_image(
        output_dir / "annotated.png",
        draw_landmarks(image, selected_source_coords, args.draw_indices),
    )

    comparisons = {}
    if args.reference_input is not None:
        comparisons["input_tensor"] = compare_arrays(
            input_tensor, args.reference_input.expanduser().resolve(), "input"
        )
    if args.reference_heatmap is not None:
        if raw_heatmap is None:
            raise RuntimeError("Cannot compare heatmaps: the ONNX has no heatmap output.")
        comparisons["heatmap"] = compare_arrays(
            raw_heatmap, args.reference_heatmap.expanduser().resolve(), "heatmap"
        )
    if args.reference_landmarks is not None:
        comparisons["landmarks_source"] = compare_arrays(
            selected_source_coords,
            args.reference_landmarks.expanduser().resolve(),
            "landmarks",
        )

    result = {
        "purpose": "pure HRNet ONNX landmark inference; no YOLO/tracking/eye selection/UI",
        "mode": mode,
        "decode": selected_space,
        "strict_current_app_hrnet_stage": bool(mode == "app_bbox" and args.decode == "app"),
        "image": {
            "path": str(image_path),
            "shape_hwc": list(image.shape),
            "bbox_xyxy": args.bbox,
        },
        "crop": (
            {
                "expand_ratio": args.expand_ratio,
                "center": crop_info["center"],
                "scale": crop_info["scale"],
                "virtual_box_xyxy": crop_info["virtual_box"],
                "out_of_image_area_is_black": True,
            }
            if crop_info is not None
            else {
                "expand_ratio": None,
                "description": "input image treated as an already prepared face crop",
            }
        ),
        "preprocess": {
            "resize_wh": input_size,
            "resize_interpolation": "cv2.INTER_LINEAR",
            "color": "BGR to RGB",
            "scale": "float32 / 255.0",
            "mean_rgb": [0.485, 0.456, 0.406],
            "std_rgb": [0.229, 0.224, 0.225],
            "layout": "NCHW",
        },
        "model": {
            "path": str(Path(landmarker.onnx_path).resolve()),
            "sha256": model_sha256,
            "providers": landmarker.session.get_providers(),
            "inputs": output_metadata(landmarker.session.get_inputs()),
            "outputs": output_metadata(landmarker.session.get_outputs()),
        },
        "inference_ms": inference_ms,
        "heatmap_size_wh": heatmap_size,
        "landmark_count": int(selected_source_coords.shape[0]),
        "landmarks_input_xy": selected_input_coords,
        "landmarks_source_xy": selected_source_coords,
        "landmark_scores": selected_scores,
        "comparisons": comparisons,
        "artifacts": {
            "annotated": str(output_dir / "annotated.png"),
            "face_crop": str(output_dir / "face_crop.png"),
            "model_input": str(output_dir / "model_input.png"),
            "model_input_annotated": str(output_dir / "model_input_annotated.png"),
            "debug_arrays": str(arrays_path),
        },
        "comparison_order": [
            "input_tensor",
            "raw heatmap",
            "heatmap decode and coordinate mapping",
        ],
    }
    result_path = output_dir / "result.json"
    with result_path.open("w", encoding="utf-8") as stream:
        json.dump(json_ready(result), stream, ensure_ascii=False, indent=2)
    return result


def is_path_inside(path, directory):
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False


def collect_image_paths(input_path, recursive, excluded_directory=None):
    if input_path.is_file():
        return [input_path]
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input image or directory not found: {input_path}")

    iterator = input_path.rglob("*") if recursive else input_path.iterdir()
    image_paths = []
    for path in iterator:
        if not path.is_file() or path.suffix.lower() not in IMAGE_SUFFIXES:
            continue
        resolved_path = path.resolve()
        if excluded_directory is not None and is_path_inside(resolved_path, excluded_directory):
            continue
        image_paths.append(resolved_path)
    image_paths.sort()
    if not image_paths:
        scope = "recursively" if recursive else "directly"
        raise RuntimeError(f"No supported images found {scope} in: {input_path}")
    return image_paths


def batch_item_output_dir(output_root, input_root, image_path):
    relative_path = image_path.relative_to(input_root)
    extension = image_path.suffix.lower().lstrip(".") or "image"
    return output_root / relative_path.parent / f"{image_path.stem}__{extension}"


def print_single_result(result):
    print(f"mode: {result['mode']}")
    print(f"decode: {result['decode']}")
    print(f"model sha256: {result['model']['sha256']}")
    print(f"landmarks: ({result['landmark_count']}, 2)")
    print(f"inference_ms: {result['inference_ms']:.3f}")
    print(f"annotated: {result['artifacts']['annotated']}")
    print(f"result: {Path(result['artifacts']['debug_arrays']).parent / 'result.json'}")
    print(f"arrays: {result['artifacts']['debug_arrays']}")
    if result["mode"] == "pre_cropped":
        print(
            "note: no --bbox was supplied; compare input_tensor and heatmap first, "
            "because this mode intentionally does not reproduce the app's 1.25 bbox crop."
        )
    if result["comparisons"]:
        print("comparisons:")
        print(json.dumps(json_ready(result["comparisons"]), ensure_ascii=False, indent=2))


def main():
    args = parse_args()
    input_path = args.image.expanduser().resolve()
    onnx_path = args.onnx_path.expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input image or directory not found: {input_path}")
    if not onnx_path.is_file():
        raise FileNotFoundError(f"ONNX model not found: {onnx_path}")
    if args.expand_ratio <= 0:
        raise ValueError("--expand-ratio must be positive.")

    batch_mode = input_path.is_dir()
    reference_paths = (
        args.reference_input,
        args.reference_heatmap,
        args.reference_landmarks,
    )
    if batch_mode and any(path is not None for path in reference_paths):
        raise ValueError(
            "--reference-input, --reference-heatmap and --reference-landmarks "
            "are only supported when --image is one file."
        )

    if args.output_dir is not None:
        output_root = args.output_dir.expanduser().resolve()
    elif batch_mode:
        output_root = input_path.parent / f"{input_path.name}_hrnet_onnx"
    else:
        output_root = input_path.parent / f"{input_path.stem}_hrnet_onnx"

    if batch_mode and output_root == input_path:
        raise ValueError("For directory inference, --output-dir cannot be the input directory itself.")
    excluded_directory = output_root if batch_mode and is_path_inside(output_root, input_path) else None
    image_paths = collect_image_paths(input_path, args.recursive, excluded_directory)
    output_root.mkdir(parents=True, exist_ok=True)

    input_size = tuple(args.input_size)
    landmarker = HRNetONNX(
        onnx_path=onnx_path,
        input_size=input_size,
        ctx_id=args.ctx_id,
        output_type="auto",
        norm_type="imagenet",
        coords_are_normalized=False,
        face_expand_ratio=args.expand_ratio,
    )

    model_input = landmarker.session.get_inputs()[0]
    static_shape = model_input.shape
    expected_shape = [1, 3, input_size[1], input_size[0]]
    if all(isinstance(value, int) for value in static_shape) and list(static_shape) != expected_shape:
        raise RuntimeError(
            f"--input-size produces {expected_shape}, but model expects {static_shape}."
        )
    model_sha256 = sha256_file(onnx_path)

    if not batch_mode:
        result = infer_one(
            args,
            input_path,
            output_root,
            landmarker,
            model_sha256,
        )
        print_single_result(result)
        return

    print(f"model: {onnx_path}")
    print(f"model sha256: {model_sha256}")
    print(f"images: {len(image_paths)}")
    print(f"output: {output_root}")
    if args.bbox is None:
        print(
            "note: each file is treated as an already cropped face because no --bbox was supplied."
        )
    else:
        print(f"note: the same --bbox {args.bbox} will be applied to every image.")

    records = []
    success_count = 0
    for index, image_path in enumerate(image_paths, start=1):
        relative_path = image_path.relative_to(input_path)
        item_output_dir = batch_item_output_dir(output_root, input_path, image_path)
        try:
            result = infer_one(
                args,
                image_path,
                item_output_dir,
                landmarker,
                model_sha256,
            )
        except Exception as exc:
            records.append(
                {
                    "image": str(image_path),
                    "relative_image": str(relative_path),
                    "status": "error",
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            print(f"[{index}/{len(image_paths)}] ERROR {relative_path}: {exc}")
            continue

        success_count += 1
        records.append(
            {
                "image": str(image_path),
                "relative_image": str(relative_path),
                "status": "ok",
                "output_dir": str(item_output_dir),
                "annotated": result["artifacts"]["annotated"],
                "result_json": str(item_output_dir / "result.json"),
                "inference_ms": result["inference_ms"],
                "landmark_count": result["landmark_count"],
                "mode": result["mode"],
                "decode": result["decode"],
            }
        )
        print(
            f"[{index}/{len(image_paths)}] OK {relative_path} "
            f"({result['inference_ms']:.1f} ms)"
        )

    summary = {
        "input_directory": str(input_path),
        "recursive": bool(args.recursive),
        "output_directory": str(output_root),
        "model": {
            "path": str(onnx_path),
            "sha256": model_sha256,
            "providers": landmarker.session.get_providers(),
        },
        "decode_requested": args.decode,
        "bbox_applied_to_every_image": args.bbox,
        "total": len(image_paths),
        "succeeded": success_count,
        "failed": len(image_paths) - success_count,
        "images": records,
    }
    summary_path = output_root / "batch_summary.json"
    with summary_path.open("w", encoding="utf-8") as stream:
        json.dump(json_ready(summary), stream, ensure_ascii=False, indent=2)

    print(
        f"batch finished: {summary['succeeded']} succeeded, "
        f"{summary['failed']} failed"
    )
    print(f"summary: {summary_path}")
    if summary["failed"] > 0:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
