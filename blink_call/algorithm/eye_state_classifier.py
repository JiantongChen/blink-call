import json
import time
from enum import Enum
from pathlib import Path

import cv2
import numpy as np
from PIL import Image
from PySide6.QtCore import QStandardPaths

from blink_call.utils.helper import Helper

ViTA_ROOT_PATH = (
    Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    / "blink_call"
    / "blink_call_model_files"
    / "ViTA"
)


class EyeState(Enum):
    CLOSE = "closed"
    OPEN = "open"
    NOT_EXIST = "not_exist"
    NOT_SURE = "not_sure"
    UNKNOWN = "unknown"


class EyeStateClassifier:
    """
    ONNXRuntime eye-state classifier.

    Public output states stay compatible with the blink-call pipeline:
    "closed", "open", "not_exist", "not_sure", or "unknown".
    """

    def __init__(self, configs):
        configs = configs or {}
        legacy_confidence_thresh = configs.get("confidence_thresh")
        self.open_confidence_thresh = float(
            configs.get(
                "open_confidence_thresh",
                0.75 if legacy_confidence_thresh is None else legacy_confidence_thresh,
            )
        )
        self.closed_confidence_thresh = float(
            configs.get(
                "closed_confidence_thresh",
                0.75 if legacy_confidence_thresh is None else legacy_confidence_thresh,
            )
        )
        self.debug_save_inputs = bool(configs.get("debug_save_inputs", False))
        self.debug_input_interval_s = max(0.0, float(configs.get("debug_input_interval_s", 0.5)))
        configured_debug_dir = configs.get("debug_input_dir")
        if configured_debug_dir:
            self.debug_input_dir = Path(str(configured_debug_dir)).expanduser()
        else:
            self.debug_input_dir = Path.home() / "Desktop" / "blink_classifier_inputs"
        self._debug_input_last_saved_s = 0.0
        self._debug_input_counter = 0
        self._debug_input_save_error = ""

        self.init_metadata()
        self.load_model()

    def init_metadata(self):
        metadata_path = ViTA_ROOT_PATH / "eye_state_classification.json"
        metadata = Helper.read_json(metadata_path, {})

        self.class_names = metadata.get(
            "class_names", [EyeState.CLOSE.value, EyeState.OPEN.value, "irrelevant"]
        )
        self.input_name = metadata.get("input_name", "images")
        self.output_name = metadata.get("output_name", "logits")

        preprocess = metadata.get("preprocess", {})
        self.resize_wh = tuple(int(value) for value in preprocess.get("resize", [128, 128]))
        self.interpolation = str(preprocess.get("interpolation", "bilinear")).lower()
        self.input_scale = float(preprocess.get("input_scale", 255.0))
        self.color_order = str(preprocess.get("color_order", "RGB")).upper()
        if self.input_scale <= 0:
            raise ValueError(f"preprocess.input_scale must be positive, got {self.input_scale}")
        if self.color_order != "RGB":
            raise ValueError(f"Unsupported classifier color_order: {self.color_order}")
        self.mean = np.array(preprocess.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32).reshape(1, 1, 3)
        self.std = np.array(preprocess.get("std", [0.229, 0.224, 0.225]), dtype=np.float32).reshape(1, 1, 3)

    def load_model(self):
        model_path = ViTA_ROOT_PATH / "eye_state_classification.onnx"
        self.session = None
        self.load_error = ""

        try:
            self.session = Helper.create_ort_session(str(model_path.resolve()), ctx_id=-1)
            input_names = {node.name for node in self.session.get_inputs()}
            output_names = {node.name for node in self.session.get_outputs()}
            if self.input_name not in input_names:
                raise ValueError(f"metadata input_name={self.input_name!r} not in model inputs={sorted(input_names)}")
            if self.output_name not in output_names:
                raise ValueError(f"metadata output_name={self.output_name!r} not in model outputs={sorted(output_names)}")
            self.model_input_shape = tuple(self.session.get_inputs()[0].shape)
            self.model_output_shape = tuple(self.session.get_outputs()[0].shape)
            self._validate_model_shapes()
        except Exception as exc:
            self.load_error = str(exc)
            self.model_input_shape = None
            self.model_output_shape = None

    def _validate_model_shapes(self):
        if len(self.model_input_shape) != 4:
            raise ValueError(f"unexpected_model_input_shape={self.model_input_shape}")

        channels = self.model_input_shape[1]
        height = self.model_input_shape[2]
        width = self.model_input_shape[3]
        if isinstance(channels, int) and channels != 3:
            raise ValueError(f"model expects {channels} channels, metadata color_order={self.color_order}")
        if isinstance(height, int) and height != self.resize_wh[1]:
            raise ValueError(
                f"model height={height} does not match metadata resize={self.resize_wh}"
            )
        if isinstance(width, int) and width != self.resize_wh[0]:
            raise ValueError(
                f"model width={width} does not match metadata resize={self.resize_wh}"
            )

        if self.model_output_shape and len(self.model_output_shape) >= 2:
            class_count = self.model_output_shape[-1]
            if isinstance(class_count, int) and class_count != len(self.class_names):
                raise ValueError(
                    f"model classes={class_count} does not match metadata class_names={len(self.class_names)}"
                )

    def classify(self, eye_roi, debug_context=None):
        if eye_roi is None:
            return self._return_data(debug_info="eye roi is None")

        if self.session is None:
            return self._return_data(debug_info=f"load model error: {self.load_error}")

        started = time.perf_counter()
        try:
            if self.debug_save_inputs:
                image_batch, preprocess_debug = self._preprocess(eye_roi, return_debug=True)
            else:
                image_batch = self._preprocess(eye_roi)

            logits = self.session.run([self.output_name], {self.input_name: image_batch})[0]
            logits = np.asarray(logits, dtype=np.float32)
            if logits.ndim == 2:
                logits = logits[0]
            if logits.ndim != 1 or logits.size == 0:
                raise ValueError(f"unexpected_logits_shape={tuple(logits.shape)}")

            pred_idx = int(np.argmax(logits))
            model_label = self.class_names[pred_idx] if pred_idx < len(self.class_names) else str(pred_idx)
            probabilities = self._softmax(logits)
            confidence = float(probabilities[pred_idx])
            confidence_thresh = {
                EyeState.OPEN.value: self.open_confidence_thresh,
                EyeState.CLOSE.value: self.closed_confidence_thresh,
            }.get(model_label)
            state = (
                model_label
                if confidence_thresh is not None and confidence > confidence_thresh
                else EyeState.NOT_SURE
            )
            if self.debug_save_inputs:
                self._save_debug_inputs(
                    eye_roi,
                    preprocess_debug,
                    debug_context,
                    prediction_label=model_label,
                    prediction_confidence=confidence,
                )
            elapsed_ms = (time.perf_counter() - started) * 1000.0
            logits_text = ",".join(f"{float(value):.4f}" for value in logits)
            probabilities_text = ",".join(f"{float(value):.4f}" for value in probabilities)
            input_min = float(np.min(image_batch))
            input_max = float(np.max(image_batch))

            return self._return_data(
                state=state,
                confidence=confidence,
                debug_info=(
                    f"label={model_label}, confidence={confidence:.3f}, state={state}, "
                    f"confidence_thresh={confidence_thresh}, "
                    f"logits=[{logits_text}], probs=[{probabilities_text}], "
                    f"roi_shape={tuple(eye_roi.shape)}, input_range=[{input_min:.3f},{input_max:.3f}], "
                    f"resize={self.resize_wh}, interpolation={self.interpolation}, "
                    f"model_input_shape={self.model_input_shape}, elapsed_ms={elapsed_ms:.1f}"
                    + (f", debug_input_save_error={self._debug_input_save_error}" if self._debug_input_save_error else "")
                ),
            )
        except Exception as exc:
            return self._return_data(debug_info=f"inference_error: {exc}")

    def _preprocess(self, eye_roi, return_debug=False):
        if not hasattr(eye_roi, "shape") or eye_roi.size == 0:
            raise ValueError("empty_eye_roi")

        if eye_roi.ndim == 2:
            rgb = cv2.cvtColor(eye_roi, cv2.COLOR_GRAY2RGB)
        elif eye_roi.ndim == 3 and eye_roi.shape[2] == 4:
            rgb = cv2.cvtColor(eye_roi, cv2.COLOR_BGRA2RGB)
        elif eye_roi.ndim == 3 and eye_roi.shape[2] == 3:
            rgb = cv2.cvtColor(eye_roi, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError(f"unexpected_eye_roi_shape={tuple(eye_roi.shape)}")

        rgb = self._pad_to_square(rgb)

        if self.interpolation not in {"bilinear", "linear"}:
            raise ValueError(f"Unsupported classifier interpolation: {self.interpolation}")

        # ViTA training uses torchvision/PIL bilinear resize with antialiasing.
        # Keep the deployment path on the same PIL implementation instead of
        # using OpenCV INTER_AREA/INTER_LINEAR.
        resized = Image.fromarray(rgb, mode="RGB").resize(
            self.resize_wh,
            Image.Resampling.BILINEAR,
        )
        image = np.asarray(resized, dtype=np.float32)
        if image.max(initial=0.0) > 1.0:
            image /= self.input_scale

        image = (image - self.mean) / self.std
        image = np.transpose(image, (2, 0, 1))[None, ...]

        image_batch = np.ascontiguousarray(image, dtype=np.float32)
        if return_debug:
            return image_batch, {
                "rgb": rgb,
                "resized_rgb": np.asarray(resized, dtype=np.uint8),
            }
        return image_batch

    def _save_debug_inputs(
        self,
        eye_roi,
        preprocess_debug,
        debug_context,
        prediction_label,
        prediction_confidence,
    ):
        now = time.perf_counter()
        if self.debug_input_interval_s > 0 and now - self._debug_input_last_saved_s < self.debug_input_interval_s:
            return

        try:
            self.debug_input_dir.mkdir(parents=True, exist_ok=True)
            self._debug_input_last_saved_s = now
            self._debug_input_counter += 1
            timestamp_ms = int(time.time() * 1000)
            stem = f"{timestamp_ms}_{self._debug_input_counter:06d}"

            raw_bgr = self._as_bgr(eye_roi)
            padded_rgb = preprocess_debug["rgb"]
            resized_rgb = preprocess_debug["resized_rgb"]
            images = {
                "raw_roi": raw_bgr,
                "padded_roi": cv2.cvtColor(padded_rgb, cv2.COLOR_RGB2BGR),
                "model_128_rgb": cv2.cvtColor(resized_rgb, cv2.COLOR_RGB2BGR),
            }
            files = {}
            for image_name, image in images.items():
                original_name = f"{stem}_{image_name}.png"
                labeled_name = f"{stem}_{image_name}_labeled.png"
                cv2.imwrite(str(self.debug_input_dir / original_name), image)
                cv2.imwrite(
                    str(self.debug_input_dir / labeled_name),
                    self._add_prediction_label(
                        image,
                        prediction_label,
                        prediction_confidence,
                    ),
                )
                files[image_name] = original_name
                files[f"{image_name}_labeled"] = labeled_name

            metadata = {
                "timestamp_ms": timestamp_ms,
                "raw_roi_shape": list(eye_roi.shape),
                "padded_roi_shape": list(padded_rgb.shape),
                "model_image_shape": list(resized_rgb.shape),
                "prediction": {
                    "label": prediction_label,
                    "confidence": float(prediction_confidence),
                },
                "eye_bbox_xyxy": (debug_context or {}).get("eye_bbox_xyxy"),
                "detector_eye_bbox_xyxy": (debug_context or {}).get("detector_eye_bbox_xyxy"),
                "classifier_input_roi_scale": (debug_context or {}).get("classifier_input_roi_scale"),
                "face_bbox_xyxy": (debug_context or {}).get("face_bbox_xyxy"),
                "raw_face_bbox_xyxy": (debug_context or {}).get("raw_face_bbox_xyxy"),
                "frame_shape": (debug_context or {}).get("frame_shape"),
                "files": files,
            }
            with (self.debug_input_dir / "metadata.jsonl").open("a", encoding="utf-8") as metadata_file:
                metadata_file.write(json.dumps(metadata, ensure_ascii=False) + "\n")
            self._debug_input_save_error = ""
        except Exception as exc:
            # Image capture is diagnostic only and must never break inference.
            self._debug_input_save_error = str(exc)

    @staticmethod
    def _add_prediction_label(image, prediction_label, prediction_confidence):
        """Add a non-destructive label band above an image for visual diagnosis."""
        label = f"pred={prediction_label} conf={prediction_confidence:.3f}"
        font = cv2.FONT_HERSHEY_SIMPLEX
        height, width = image.shape[:2]
        font_scale = max(0.35, min(0.7, width / 240.0))
        thickness = max(1, int(round(width / 120.0)))
        text_size, baseline = cv2.getTextSize(label, font, font_scale, thickness)
        padding = max(3, int(round(min(height, width) * 0.04)))
        band_height = text_size[1] + baseline + padding * 2

        labeled = np.zeros((height + band_height, width, 3), dtype=np.uint8)
        labeled[band_height:] = image
        cv2.rectangle(labeled, (0, 0), (width - 1, band_height - 1), (25, 25, 25), -1)
        text_y = padding + text_size[1]
        cv2.putText(
            labeled,
            label,
            (padding, text_y),
            font,
            font_scale,
            (255, 255, 255),
            thickness,
            cv2.LINE_AA,
        )
        return labeled

    @staticmethod
    def _as_bgr(image):
        if image.ndim == 2:
            return cv2.cvtColor(image, cv2.COLOR_GRAY2BGR)
        if image.ndim == 3 and image.shape[2] == 4:
            return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        if image.ndim == 3 and image.shape[2] == 3:
            return image
        raise ValueError(f"unexpected_eye_roi_shape={tuple(image.shape)}")

    @staticmethod
    def _pad_to_square(image):
        """Pad an ROI to a square without cropping its visual content."""
        height, width = image.shape[:2]
        if height == width:
            return image

        target_size = max(height, width)
        if width < target_size:
            padding = target_size - width
            left = padding // 2
            right = padding - left
            return cv2.copyMakeBorder(
                image,
                0,
                0,
                left,
                right,
                borderType=cv2.BORDER_REPLICATE,
            )

        padding = target_size - height
        top = padding // 2
        bottom = padding - top
        return cv2.copyMakeBorder(
            image,
            top,
            bottom,
            0,
            0,
            borderType=cv2.BORDER_REPLICATE,
        )

    def _softmax(self, logits):
        shifted = logits - np.max(logits)
        exp = np.exp(shifted)
        return exp / np.sum(exp)

    def _return_data(self, state=EyeState.UNKNOWN, confidence=-1, debug_info=""):
        return {
            "timestamp_ms": int(time.time() * 1000),
            "state": state,
            "confidence": confidence,
            "debug_info": debug_info,
        }
