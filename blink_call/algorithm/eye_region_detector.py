import time
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QStandardPaths
from blink_call.utils.head_pose_estimator import InsightFaceHeadPose
from blink_call.utils.helper import Helper
from blink_call.algorithm.inference import RetinaFaceONNX, HRNetONNX


APP_MODEL_ROOT = (
    Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    / "blink_call"
    / "blink_call_model_files"
)


class EyeRegionDetector:
    """
    Two-stage eye-region detector:
        1. local RetinaFace ONNX for face detection
        2. local HRNet ONNX for landmark detection

    Eye selection rule:
        Same as the original InsightFace-only version:
            yaw > 0  -> left eye
            yaw <= 0 -> right eye
    """

    def __init__(self, configs):
        self.ctx_id = int(configs.get("ctx_id", -1))
        self.det_size = tuple(configs.get("det_size", (640, 640)))
        self.det_thresh = float(configs.get("det_thresh", 0.8))
        self.det_nms_thresh = float(configs.get("det_nms_thresh", 0.3))
        self.eye_padding = int(configs.get("eye_padding", 20))
        self.max_num_faces = int(configs.get("max_num_faces", 1))

        default_retina_path = APP_MODEL_ROOT / "retinaface" / "retinaface.onnx"
        default_hrnet_path = APP_MODEL_ROOT / "hrnet" / "hrnet_wflw_98_coords.onnx"

        self.retina_onnx_path = str(configs.get("retina_onnx_path", default_retina_path))
        self.hrnet_onnx_path = str(configs.get("hrnet_onnx_path", default_hrnet_path))

        self.retina_cls_is_score = bool(configs.get("retina_cls_is_score", True))

        self.hrnet_input_size = tuple(configs.get("hrnet_input_size", (256, 256)))
        self.hrnet_output_type = str(configs.get("hrnet_output_type", "coords"))
        self.hrnet_norm_type = str(configs.get("hrnet_norm_type", "imagenet"))
        self.hrnet_coords_are_normalized = bool(
            configs.get("hrnet_coords_are_normalized", False)
        )
        self.face_expand_ratio = float(configs.get("face_expand_ratio", 1.25))

        self.face_detector = RetinaFaceONNX(
            onnx_path=self.retina_onnx_path,
            input_size=self.det_size,
            ctx_id=self.ctx_id,
            score_thresh=self.det_thresh,
            nms_thresh=self.det_nms_thresh,
            cls_is_score=self.retina_cls_is_score,
        )

        self.landmarker = HRNetONNX(
            onnx_path=self.hrnet_onnx_path,
            input_size=self.hrnet_input_size,
            ctx_id=self.ctx_id,
            output_type=self.hrnet_output_type,
            norm_type=self.hrnet_norm_type,
            coords_are_normalized=self.hrnet_coords_are_normalized,
            face_expand_ratio=self.face_expand_ratio,
        )

        self.eye_indices = configs.get(
            "eye_indices",
            {
                "left": list(range(60, 68)),
                "right": list(range(68, 76)),
            },
        )

        self.head_pose_estimator = InsightFaceHeadPose()

    def _select_eye(self, landmarks, frame_shape):
        head_pose = self.head_pose_estimator.estimate(landmarks, frame_shape)
        selected_eye = "right" if head_pose["yaw"] > 0 else "left"
        return selected_eye, head_pose

    def detect(self, frame):
        if frame is None:
            return self._return_data(debug_info="frame is None")

        if not isinstance(frame, np.ndarray) or frame.ndim < 2:
            return self._return_data(debug_info="invalid frame data")

        t0 = time.perf_counter()
        try:
            faces, landmarks5 = self.face_detector.detect(frame)
        except Exception as exc:
            return self._return_data(debug_info=f"retinaface onnx inference error: {exc}")

        if faces.shape[0] == 0:
            return self._return_data(debug_info="no face detected")

        if faces.shape[0] > 1:
            areas = (faces[:, 2] - faces[:, 0]) * (faces[:, 3] - faces[:, 1])
            face_idx = int(np.argmax(areas))
        else:
            face_idx = 0

        face = faces[face_idx]
        face_bbox = face[:4].tolist()
        t1 = time.perf_counter()

        try:
            landmarks, crop_box = self.landmarker.infer(frame, face_bbox)
        except Exception as exc:
            return self._return_data(debug_info=f"hrnet onnx inference error: {exc}")

        if landmarks is None or landmarks.ndim != 2 or landmarks.shape[1] != 2:
            bad_shape = None if landmarks is None else landmarks.shape
            return self._return_data(debug_info=f"invalid landmarks predicted: {bad_shape}")

        try:
            left_eye_points = landmarks[self.eye_indices["left"]]
            right_eye_points = landmarks[self.eye_indices["right"]]
        except Exception as exc:
            return self._return_data(debug_info=f"eye index error: {exc}")

        try:
            selected_eye, head_pose = self._select_eye(landmarks, frame.shape)
        except Exception as exc:
            return self._return_data(debug_info=f"head pose estimation error: {exc}")

        selected_points = left_eye_points if selected_eye == "left" else right_eye_points
        eye_bbox = Helper.points_to_bbox(selected_points, frame.shape, padding=self.eye_padding)
        t2 = time.perf_counter()

        debug_info = (
            f"select {selected_eye} eye: "
            f"det_ms={(t1 - t0) * 1000.0:.1f}, "
            f"lmk_ms={(t2 - t1) * 1000.0:.1f}, "
            f"total_ms={(t2 - t0) * 1000.0:.1f}, "
            f"yaw:{head_pose['yaw']:.3f}, "
            f"pitch:{head_pose['pitch']:.3f}, "
            f"roll:{head_pose['roll']:.3f}"
        )
        if crop_box is not None:
            debug_info += f", crop_box={list(map(int, crop_box))}"

        return self._return_data(
            eye_bbox_xyxy=eye_bbox,
            face_bbox_xyxy=[float(v) for v in face_bbox],
            landmarks=landmarks.tolist(),
            debug_info=debug_info,
        )

    def _return_data(
        self,
        eye_bbox_xyxy=None,
        face_bbox_xyxy=None,
        landmarks=None,
        debug_info="",
    ):
        return {
            "timestamp_ms": int(time.time() * 1000),
            "eye_bbox_xyxy": eye_bbox_xyxy,
            "face_bbox_xyxy": face_bbox_xyxy,
            "landmarks": landmarks,
            "debug_info": debug_info,
        }
