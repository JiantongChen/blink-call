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
            score_thresh=float(configs.get("det_thresh", 0.8)),
            nms_thresh=float(configs.get("det_nms_thresh", 0.3)),
            cls_is_score=bool(configs.get("retina_cls_is_score", True)),
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

    def detect(self, frame):
        if frame is None:
            return self._return_data(debug_info="frame is None")

        if not isinstance(frame, np.ndarray) or frame.ndim < 2:
            return self._return_data(debug_info="invalid frame data")

        # 1. Face region detection
        t0 = time.perf_counter()
        try:
            faces, landmarks5 = self.face_detector.detect(frame)
        except Exception as exc:
            return self._return_data(debug_info=f"retinaface onnx inference error: {exc}")

        if faces.shape[0] == 0:
            return self._return_data(debug_info="no face detected")

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
            left_score = np.mean(landmark_scores[self.eye_indices["left"]])
            right_score = np.mean(landmark_scores[self.eye_indices["right"]])

            if left_score >= right_score:
                selected_eye = "left"
                selected_points = landmarks[self.eye_indices["left"]]
            else:
                selected_eye = "right"
                selected_points = landmarks[self.eye_indices["right"]]

            eye_bbox = Helper.points_to_bbox(selected_points, frame.shape, padding=self.eye_padding)
        except Exception as exc:
            return self._return_data(debug_info=f"eye selection error: {exc}")

        debug_info = (
            f"select {selected_eye} eye: "
            f"left_score={left_score:.3f}, "
            f"right_score={right_score:.3f}, "
            f"det_ms={(t1 - t0) * 1000.0:.1f}, "
            f"lmk_ms={(t2 - t1) * 1000.0:.1f}, "
            f"total_ms={(time.perf_counter() - t0) * 1000.0:.1f}"
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
