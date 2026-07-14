import time
from pathlib import Path

import numpy as np
from PySide6.QtCore import QStandardPaths

from blink_call.algorithm.inference import HRNetONNX, RetinaFaceONNX
from blink_call.utils.helper import Helper

APP_MODEL_ROOT = (
    Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "blink_call" / "blink_call_model_files"
)


class EyeRegionDetector:
    """
    Two-stage eye-region detector:
        1. local RetinaFace ONNX for face detection
        2. local HRNet ONNX for landmark detection
    """

    def __init__(self, configs):
        self.retina_onnx_path = str(configs.get("retina_onnx_path", APP_MODEL_ROOT / "retinaface" / "retinaface.onnx"))
        self.hrnet_onnx_path = str(configs.get("hrnet_onnx_path", APP_MODEL_ROOT / "hrnet" / "hrnet.onnx"))

        self.face_detector = RetinaFaceONNX(
            onnx_path=self.retina_onnx_path,
            input_size=tuple(configs.get("det_size", (640, 640))),
            ctx_id=int(configs.get("ctx_id", -1)),
            score_thresh=float(configs.get("det_thresh", 0.3)),
            nms_thresh=float(configs.get("det_nms_thresh", 0.3)),
            cls_is_score=bool(configs.get("retina_cls_is_score", True)),
            bgr_to_rgb=bool(configs.get("retina_bgr_to_rgb", True)),
        )

        self.landmarker = HRNetONNX(
            onnx_path=self.hrnet_onnx_path,
            input_size=tuple(configs.get("hrnet_input_size", (256, 256))),
            ctx_id=int(configs.get("ctx_id", -1)),
            output_type=str(configs.get("hrnet_output_type", "auto")),
            norm_type=str(configs.get("hrnet_norm_type", "imagenet")),
            coords_are_normalized=bool(configs.get("hrnet_coords_are_normalized", False)),
            face_expand_ratio=float(configs.get("face_expand_ratio", 1.25)),
        )

        # landmark indices: https://wywu.github.io/projects/LAB/WFLW.html
        self.eye_indices = {
            "left": list(range(68, 76)),
            "right": list(range(60, 68)),
        }
        self.eye_padding = int(configs.get("eye_padding", 20))
        self.eye_padding_ratio = float(configs.get("eye_padding_ratio", 0.06))
        self.min_eye_padding = int(configs.get("min_eye_padding", 4))

        # A full camera frame makes a distant face very small at the detector's
        # fixed input resolution.  Once a face has been found, search a region
        # around its last position so that it occupies more detector pixels.
        self.tracking_roi_scale = float(configs.get("tracking_roi_scale", 3.0))
        self.fallback_crop_ratio = float(configs.get("fallback_crop_ratio", 0.65))

        self.eye_switch_margin = float(configs.get("eye_switch_margin", 0.08))
        self.eye_switch_confirm_frames = int(configs.get("eye_switch_confirm_frames", 5))
        self.eye_near_weight = float(configs.get("eye_near_weight", 0.12))
        self.eye_bad_score_thresh = float(configs.get("eye_bad_score_thresh", 0.65))
        self.eye_bad_confirm_frames = int(configs.get("eye_bad_confirm_frames", 3))
        self.locked_eye = None
        self.switch_candidate = None
        self.switch_count = 0
        self.bad_count = 0

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
            return np.zeros((0, 5), dtype=np.float32)

        faces, _ = self.face_detector.detect(roi)
        if faces.shape[0] == 0:
            return faces

        faces = faces.copy()
        faces[:, [0, 2]] += x1
        faces[:, [1, 3]] += y1
        return faces

    @staticmethod
    def _eye_score(landmark_scores, indices):
        if landmark_scores is None:
            return {"score": 1.0, "mean": 1.0, "min": 1.0}

        scores = np.asarray(landmark_scores[indices], dtype=np.float32)
        if scores.size == 0:
            return {"score": 0.0, "mean": 0.0, "min": 0.0}

        mean_score = float(np.mean(scores))
        min_score = float(np.min(scores))
        return {"score": 0.8 * mean_score + 0.2 * min_score, "mean": mean_score, "min": min_score}

    @staticmethod
    def _eye_nearness_score(landmarks, indices):
        points = np.asarray(landmarks[indices], dtype=np.float32)
        if points.size == 0:
            return 0.0

        width = float(np.max(points[:, 0]) - np.min(points[:, 0]))
        height = float(np.max(points[:, 1]) - np.min(points[:, 1]))
        return max(0.0, width) * max(0.0, height)

    def _select_stable_eye(self, landmarks, landmark_scores):
        left = self._eye_score(landmark_scores, self.eye_indices["left"])
        right = self._eye_score(landmark_scores, self.eye_indices["right"])

        left_near = self._eye_nearness_score(landmarks, self.eye_indices["left"])
        right_near = self._eye_nearness_score(landmarks, self.eye_indices["right"])
        near_total = max(left_near + right_near, 1.0)
        left_near_ratio = left_near / near_total
        right_near_ratio = right_near / near_total

        left_total = left["score"] + self.eye_near_weight * left_near_ratio
        right_total = right["score"] + self.eye_near_weight * right_near_ratio
        scores = {
            "left": {**left, "near": left_near_ratio, "total": left_total},
            "right": {**right, "near": right_near_ratio, "total": right_total},
        }

        if self.locked_eye is None:
            self.locked_eye = "left" if left_total >= right_total else "right"
            reason = "initial"
        else:
            reason = "locked"

        current_eye = self.locked_eye
        other_eye = "right" if current_eye == "left" else "left"
        current_score = scores[current_eye]["total"]
        other_score = scores[other_eye]["total"]
        current_confidence = scores[current_eye]["score"]
        other_confidence = scores[other_eye]["score"]

        if current_confidence < self.eye_bad_score_thresh and other_score > current_score:
            self.bad_count += 1
        else:
            self.bad_count = 0

        score_gap = other_score - current_score
        should_consider_switch = score_gap >= self.eye_switch_margin or self.bad_count >= self.eye_bad_confirm_frames

        if should_consider_switch:
            if self.switch_candidate == other_eye:
                self.switch_count += 1
            else:
                self.switch_candidate = other_eye
                self.switch_count = 1

            if self.switch_count >= self.eye_switch_confirm_frames:
                self.locked_eye = other_eye
                self.switch_candidate = None
                self.switch_count = 0
                self.bad_count = 0
                reason = "switch_confirmed"
            else:
                reason = f"switch_pending_{self.switch_count}/{self.eye_switch_confirm_frames}"
        else:
            self.switch_candidate = None
            self.switch_count = 0

        return self.locked_eye, {
            "left_score": left["score"],
            "right_score": right["score"],
            "left_total": left_total,
            "right_total": right_total,
            "left_near": left_near_ratio,
            "right_near": right_near_ratio,
            "left_mean": left["mean"],
            "right_mean": right["mean"],
            "left_min": left["min"],
            "right_min": right["min"],
            "score_gap": scores["right"]["total"] - scores["left"]["total"],
            "reason": reason,
        }

    def detect(self, frame):
        if frame is None:
            return self._return_data(debug_info="frame is None")

        if not isinstance(frame, np.ndarray) or frame.ndim < 2:
            return self._return_data(debug_info="invalid frame data")

        # 1. Face region detection. Prefer a zoomed tracking ROI for distant
        # faces, then fall back to the whole frame and a centered zoom crop.
        t0 = time.perf_counter()
        try:
            detection_mode = "full"
            faces = np.zeros((0, 5), dtype=np.float32)

            if self.last_face_bbox is not None:
                tracking_roi = self._expanded_roi_box(
                    self.last_face_bbox,
                    frame.shape,
                    self.tracking_roi_scale,
                )
                faces = self._detect_in_roi(frame, tracking_roi)
                detection_mode = "tracking_roi"

            if faces.shape[0] == 0:
                faces, _ = self.face_detector.detect(frame)
                detection_mode = "full"

            if faces.shape[0] == 0 and self.fallback_crop_ratio < 1.0:
                fallback_roi = self._center_crop_box(frame.shape, self.fallback_crop_ratio)
                faces = self._detect_in_roi(frame, fallback_roi)
                detection_mode = "center_zoom"
        except Exception as exc:
            return self._return_data(debug_info=f"retinaface onnx inference error: {exc}")

        if faces.shape[0] == 0:
            self.last_face_bbox = None
            retina_debug = getattr(self.face_detector, "last_debug_info", "")
            return self._return_data(debug_info=f"no face detected; {retina_debug}")

        face = faces[np.argmax(faces[:, 4])]
        face_bbox = face[:4].tolist()

        # 2. Facial landmark detection
        t1 = time.perf_counter()
        try:
            landmarks, crop_box, landmark_scores = self.landmarker.infer(frame, face_bbox)
        except Exception as exc:
            return self._return_data(debug_info=f"hrnet onnx inference error: {exc}")

        if landmarks is None or landmarks.ndim != 2 or landmarks.shape[1] != 2:
            bad_shape = None if landmarks is None else landmarks.shape
            return self._return_data(debug_info=f"invalid landmarks predicted: {bad_shape}")

        # 3. Select eye area
        t2 = time.perf_counter()
        try:
            selected_eye, eye_score_info = self._select_stable_eye(landmarks, landmark_scores)
            selected_points = landmarks[self.eye_indices[selected_eye]]

            face_width = max(2.0, face_bbox[2] - face_bbox[0])
            adaptive_padding = int(round(face_width * self.eye_padding_ratio))
            adaptive_padding = max(
                self.min_eye_padding,
                min(self.eye_padding, adaptive_padding),
            )
            eye_bbox = Helper.points_to_bbox(selected_points, frame.shape, padding=adaptive_padding)
        except Exception as exc:
            return self._return_data(debug_info=f"eye selection error: {exc}")

        # Keep the RetinaFace box as the face-box result and tracking input.
        # HRNet landmarks are a downstream result and must not redefine it.
        self.last_face_bbox = face_bbox

        retina_debug = getattr(self.face_detector, "last_debug_info", "")
        debug_info = (
            f"select {selected_eye} eye: "
            f"left_score={eye_score_info['left_score']:.3f}, "
            f"right_score={eye_score_info['right_score']:.3f}, "
            f"left_near={eye_score_info['left_near']:.3f}, "
            f"right_near={eye_score_info['right_near']:.3f}, "
            f"left_total={eye_score_info['left_total']:.3f}, "
            f"right_total={eye_score_info['right_total']:.3f}, "
            f"left_min={eye_score_info['left_min']:.3f}, "
            f"right_min={eye_score_info['right_min']:.3f}, "
            f"score_gap={eye_score_info['score_gap']:.3f}, "
            f"reason={eye_score_info['reason']}, "
            f"switch_count={self.switch_count}, bad_count={self.bad_count}, "
            f"mode={detection_mode}, eye_padding={adaptive_padding}, "
            f"det_ms={(t1 - t0) * 1000.0:.1f}, "
            f"lmk_ms={(t2 - t1) * 1000.0:.1f}, "
            f"total_ms={(time.perf_counter() - t0) * 1000.0:.1f}, "
            f"{retina_debug}"
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
