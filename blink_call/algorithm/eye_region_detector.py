import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QStandardPaths

from blink_call.algorithm.inference import HRNetONNX, YOLOv6ONNX
from blink_call.utils.helper import Helper

APP_MODEL_ROOT = (
    Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "blink_call" / "blink_call_model_files"
)
DEFAULT_YOLOV6_ONNX_PATH = APP_MODEL_ROOT / "yolov6" / "yolov6.onnx"


class EyeRegionDetector:
    """
    Two-stage eye-region detector:
        1. fine-tuned YOLOv6-lite ONNX for face detection
        2. local HRNet ONNX for landmark detection
    """

    def __init__(self, configs):
        configs = configs or {}
        self.yolov6_onnx_path = str(configs.get("yolov6_onnx_path", DEFAULT_YOLOV6_ONNX_PATH))
        self.hrnet_onnx_path = str(configs.get("hrnet_onnx_path", APP_MODEL_ROOT / "hrnet" / "hrnet.onnx"))

        self.face_detector = YOLOv6ONNX(
            onnx_path=self.yolov6_onnx_path,
            input_size=tuple(configs.get("det_size", (640, 640))),
            ctx_id=int(configs.get("ctx_id", -1)),
            score_thresh=float(configs.get("det_thresh", 0.3)),
            nms_thresh=float(configs.get("det_nms_thresh", 0.45)),
            class_id=configs.get("yolov6_face_class_id", 0),
            max_detections=int(configs.get("det_max_detections", 100)),
        )

        self.landmarker = HRNetONNX(
            onnx_path=self.hrnet_onnx_path,
            input_size=tuple(configs.get("hrnet_input_size", (256, 256))),
            ctx_id=int(configs.get("ctx_id", -1)),
            output_type=str(configs.get("hrnet_output_type", "auto")),
            norm_type=str(configs.get("hrnet_norm_type", "imagenet")),
            coords_are_normalized=bool(configs.get("hrnet_coords_are_normalized", False)),
            face_expand_ratio=float(configs.get("face_expand_ratio", 1.0)),
        )

        # landmark indices: https://wywu.github.io/projects/LAB/WFLW.html
        self.eye_indices = {
            "left": list(range(68, 76)),
            "right": list(range(60, 68)),
        }
        self.eye_padding = int(configs.get("eye_padding", 20))
        self.eye_padding_ratio = float(configs.get("eye_padding_ratio", 0.06))
        self.min_eye_padding = int(configs.get("min_eye_padding", 4))

        # Validate an eye's eight WFLW landmarks before min/max turns them into
        # a bbox. These ratios use the longer face-box side, so they remain
        # valid for upright, tilted, and side-lying faces.
        self.eye_min_diameter_ratio = max(
            0.0,
            float(configs.get("eye_min_diameter_ratio", 0.02)),
        )
        self.eye_max_diameter_ratio = max(
            self.eye_min_diameter_ratio,
            float(configs.get("eye_max_diameter_ratio", 0.30)),
        )
        self.eye_max_edge_ratio = max(
            0.01,
            float(configs.get("eye_max_edge_ratio", 0.12)),
        )
        self.eye_center_face_margin_ratio = max(
            0.0,
            float(configs.get("eye_center_face_margin_ratio", 0.15)),
        )

        # Start with full-frame detection, then use the previous face position
        # and a centered fallback to avoid running a full YOLO pass on every
        # frame once tracking has been established.
        self.enable_tracking_roi = bool(configs.get("enable_tracking_roi", True))
        self.enable_center_zoom = bool(configs.get("enable_center_zoom", True))
        self.tracking_roi_scale = float(configs.get("tracking_roi_scale", 3.0))
        self.fallback_crop_ratio = float(configs.get("fallback_crop_ratio", 0.65))

        self.last_face_bbox = None

    @staticmethod
    def _center_crop_box(frame_shape, crop_ratio):
        h, w = frame_shape[:2]
        ratio = min(1.0, max(0.1, float(crop_ratio)))
        crop_w = max(2, int(round(w * ratio)))
        crop_h = max(2, int(round(h * ratio)))
        x1 = (w - crop_w) // 2
        y1 = (h - crop_h) // 2
        return [x1, y1, x1 + crop_w, y1 + crop_h]

    @staticmethod
    def _expanded_roi_box(face_bbox, frame_shape, scale):
        h, w = frame_shape[:2]
        x1, y1, x2, y2 = map(float, face_bbox)
        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)
        roi_w = max(2.0, (x2 - x1) * float(scale))
        roi_h = max(2.0, (y2 - y1) * float(scale))

        nx1 = max(0, int(round(cx - 0.5 * roi_w)))
        ny1 = max(0, int(round(cy - 0.5 * roi_h)))
        nx2 = min(w, int(round(cx + 0.5 * roi_w)))
        ny2 = min(h, int(round(cy + 0.5 * roi_h)))
        return [nx1, ny1, nx2, ny2]

    def _detect_in_roi(self, frame, roi_box):
        x1, y1, x2, y2 = roi_box
        roi = frame[y1:y2, x1:x2]
        if roi.size == 0:
            empty = np.zeros((0, 5), dtype=np.float32)
            return empty, empty.copy()

        faces, _ = self.face_detector.detect(roi)
        landmark_faces = self._landmark_faces_for_last_detection(faces)
        if faces.shape[0] == 0:
            return faces, landmark_faces

        faces = faces.copy()
        landmark_faces = landmark_faces.copy()
        faces[:, [0, 2]] += x1
        faces[:, [1, 3]] += y1
        landmark_faces[:, [0, 2]] += x1
        landmark_faces[:, [1, 3]] += y1
        return faces, landmark_faces

    def _landmark_faces_for_last_detection(self, clipped_faces):
        """Return score-aligned boxes before image-boundary clipping."""
        candidate = getattr(self.face_detector, "last_unclipped_detections", None)
        if candidate is None:
            return clipped_faces.copy()
        candidate = np.asarray(candidate, dtype=np.float32)
        if candidate.shape != clipped_faces.shape:
            return clipped_faces.copy()
        if candidate.size and not np.allclose(candidate[:, 4], clipped_faces[:, 4], rtol=0.0, atol=1e-6):
            return clipped_faces.copy()
        return candidate.copy()

    def _select_eye_by_confidence(self, landmark_scores):
        if landmark_scores is None:
            left_score = right_score = 1.0
        else:
            left_score = float(np.mean(landmark_scores[self.eye_indices["left"]]))
            right_score = float(np.mean(landmark_scores[self.eye_indices["right"]]))

        selected_eye = "left" if left_score >= right_score else "right"
        return selected_eye, left_score, right_score

    def _validate_eye_points(self, points, face_bbox):
        """Validate one eye ring without assuming that the face is upright."""
        points = np.asarray(points, dtype=np.float32)
        metrics = {
            "diameter_ratio": float("nan"),
            "max_edge_ratio": float("nan"),
        }

        if points.shape != (8, 2):
            return False, "invalid_shape", metrics
        if not np.all(np.isfinite(points)):
            return False, "non_finite", metrics

        x1, y1, x2, y2 = map(float, face_bbox)
        face_left, face_right = sorted((x1, x2))
        face_top, face_bottom = sorted((y1, y2))
        face_width = max(2.0, face_right - face_left)
        face_height = max(2.0, face_bottom - face_top)
        face_scale = max(face_width, face_height)

        pairwise = points[:, None, :] - points[None, :, :]
        diameter = float(np.max(np.linalg.norm(pairwise, axis=2)))
        ring_edges = np.roll(points, -1, axis=0) - points
        max_edge = float(np.max(np.linalg.norm(ring_edges, axis=1)))
        diameter_ratio = diameter / face_scale
        max_edge_ratio = max_edge / face_scale
        metrics = {
            "diameter_ratio": diameter_ratio,
            "max_edge_ratio": max_edge_ratio,
        }

        if diameter_ratio < self.eye_min_diameter_ratio:
            return False, "diameter_too_small", metrics
        if diameter_ratio > self.eye_max_diameter_ratio:
            return False, "diameter_too_large", metrics
        if max_edge_ratio > self.eye_max_edge_ratio:
            return False, "edge_too_large", metrics

        # Median prevents one outlying point from pulling the group center.
        center = np.median(points, axis=0)
        margin_x = face_width * self.eye_center_face_margin_ratio
        margin_y = face_height * self.eye_center_face_margin_ratio
        if not (
            face_left - margin_x <= float(center[0]) <= face_right + margin_x
            and face_top - margin_y <= float(center[1]) <= face_bottom + margin_y
        ):
            return False, "center_outside_face", metrics

        return True, "valid", metrics

    def _build_eye_candidate(self, landmarks, eye_label, face_bbox, frame_shape, padding):
        points = np.asarray(landmarks[self.eye_indices[eye_label]], dtype=np.float32)
        valid, reason, metrics = self._validate_eye_points(points, face_bbox)
        bbox = None
        if valid:
            bbox = Helper.points_to_bbox(points, frame_shape, padding=padding)
        return {
            "bbox": bbox,
            "valid": valid,
            "reason": reason,
            **metrics,
        }

    @staticmethod
    def _choose_geometry_valid_eye(requested_eye, candidates):
        requested = candidates[requested_eye]
        if requested["valid"]:
            return requested_eye, requested["bbox"], "requested_valid"

        other_eye = "right" if requested_eye == "left" else "left"
        other = candidates[other_eye]
        if other["valid"]:
            reason = f"fallback_to_{other_eye}:{requested_eye}_{requested['reason']}"
            return other_eye, other["bbox"], reason

        reason = (
            f"reject_both:left_{candidates['left']['reason']},"
            f"right_{candidates['right']['reason']}"
        )
        return None, None, reason

    def detect(self, frame):
        if frame is None:
            return self._return_data(debug_info="frame is None")

        if not isinstance(frame, np.ndarray) or frame.ndim < 2:
            return self._return_data(debug_info="invalid frame data")

        # 1. Face region detection.  Full-frame inference is the default so the
        # software follows the same spatial path as offline inference.  The
        # tracking and centered zoom paths are explicit opt-ins.
        t0 = time.perf_counter()
        try:
            detection_mode = "full"
            faces = np.zeros((0, 5), dtype=np.float32)
            landmark_faces = faces.copy()

            if self.enable_tracking_roi and self.last_face_bbox is not None:
                tracking_roi = self._expanded_roi_box(
                    self.last_face_bbox,
                    frame.shape,
                    self.tracking_roi_scale,
                )
                faces, landmark_faces = self._detect_in_roi(frame, tracking_roi)
                detection_mode = "tracking_roi"

            if faces.shape[0] == 0:
                faces, _ = self.face_detector.detect(frame)
                landmark_faces = self._landmark_faces_for_last_detection(faces)
                detection_mode = "full"

            if faces.shape[0] == 0 and self.enable_center_zoom and self.fallback_crop_ratio < 1.0:
                fallback_roi = self._center_crop_box(frame.shape, self.fallback_crop_ratio)
                faces, landmark_faces = self._detect_in_roi(frame, fallback_roi)
                detection_mode = "center_zoom"
        except Exception as exc:
            return self._return_data(debug_info=f"yolov6 onnx inference error: {exc}")

        if faces.shape[0] == 0:
            self.last_face_bbox = None
            detector_debug = getattr(self.face_detector, "last_debug_info", "")
            return self._return_data(debug_info=f"no face detected; mode={detection_mode}, {detector_debug}")

        face_index = int(np.argmax(faces[:, 4]))
        face = faces[face_index]
        landmark_face = landmark_faces[face_index]
        face_bbox = face[:4].tolist()
        landmark_face_bbox = landmark_face[:4].tolist()

        # 2. Facial landmark detection
        t1 = time.perf_counter()
        try:
            landmarks, crop_box, landmark_scores = self.landmarker.infer(frame, landmark_face_bbox)
        except Exception as exc:
            return self._return_data(debug_info=f"hrnet onnx inference error: {exc}")

        if landmarks is None or landmarks.ndim != 2 or landmarks.shape[1] != 2:
            bad_shape = None if landmarks is None else landmarks.shape
            return self._return_data(debug_info=f"invalid landmarks predicted: {bad_shape}")

        # 3. Select eye area
        t2 = time.perf_counter()
        try:
            requested_eye, left_score, right_score = self._select_eye_by_confidence(landmark_scores)

            face_width = max(2.0, face_bbox[2] - face_bbox[0])
            adaptive_padding = int(round(face_width * self.eye_padding_ratio))
            adaptive_padding = max(
                self.min_eye_padding,
                min(self.eye_padding, adaptive_padding),
            )
            eye_candidates = {
                eye_label: self._build_eye_candidate(
                    landmarks,
                    eye_label,
                    landmark_face_bbox,
                    frame.shape,
                    adaptive_padding,
                )
                for eye_label in ("left", "right")
            }
            selected_eye, eye_bbox, eye_geometry_reason = self._choose_geometry_valid_eye(
                requested_eye,
                eye_candidates,
            )
        except Exception as exc:
            return self._return_data(debug_info=f"eye selection error: {exc}")

        # Keep the YOLOv6 box as the face-box result and tracking input.
        # HRNet landmarks are a downstream result and must not redefine it.
        self.last_face_bbox = face_bbox

        detector_debug = getattr(self.face_detector, "last_debug_info", "")
        left_geometry = eye_candidates["left"]
        right_geometry = eye_candidates["right"]
        debug_info = (
            f"select {selected_eye or 'none'} eye: "
            f"requested_eye={requested_eye}, "
            f"left_score={left_score:.3f}, "
            f"right_score={right_score:.3f}, "
            f"geometry={eye_geometry_reason}, "
            f"left_geometry={left_geometry['reason']}"
            f"(diameter={left_geometry['diameter_ratio']:.3f},edge={left_geometry['max_edge_ratio']:.3f}), "
            f"right_geometry={right_geometry['reason']}"
            f"(diameter={right_geometry['diameter_ratio']:.3f},edge={right_geometry['max_edge_ratio']:.3f}), "
            f"mode={detection_mode}, "
            f"tracking_roi_enabled={self.enable_tracking_roi}, "
            f"center_zoom_enabled={self.enable_center_zoom}, "
            f"hrnet_unclipped_box={landmark_face_bbox != face_bbox}, "
            f"eye_padding={adaptive_padding}, "
            f"det_ms={(t1 - t0) * 1000.0:.1f}, "
            f"lmk_ms={(t2 - t1) * 1000.0:.1f}, "
            f"total_ms={(time.perf_counter() - t0) * 1000.0:.1f}, "
            f"{detector_debug}"
        )

        return self._return_data(
            eye_bbox_xyxy=eye_bbox,
            face_bbox_xyxy=[float(v) for v in face_bbox],
            landmarks=landmarks.tolist(),
            landmark_scores=None if landmark_scores is None else landmark_scores.tolist(),
            debug_info=debug_info,
        )

    def _return_data(
        self,
        eye_bbox_xyxy=None,
        face_bbox_xyxy=None,
        landmarks=None,
        landmark_scores=None,
        debug_info="",
    ):
        return {
            "timestamp_ms": int(time.time() * 1000),
            "eye_bbox_xyxy": eye_bbox_xyxy,
            "face_bbox_xyxy": face_bbox_xyxy,
            "landmarks": landmarks,
            "landmark_scores": landmark_scores,
            "debug_info": debug_info,
        }
