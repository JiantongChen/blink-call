import time
from pathlib import Path

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
        default_hrnet_path = APP_MODEL_ROOT / "hrnet" / "hrnet.onnx"

        self.retina_onnx_path = str(configs.get("retina_onnx_path", default_retina_path))
        self.hrnet_onnx_path = str(configs.get("hrnet_onnx_path", default_hrnet_path))

        self.retina_cls_is_score = bool(configs.get("retina_cls_is_score", True))

        self.hrnet_input_size = tuple(configs.get("hrnet_input_size", (256, 256)))
        self.hrnet_output_type = str(configs.get("hrnet_output_type", "auto"))
        self.hrnet_norm_type = str(configs.get("hrnet_norm_type", "imagenet"))
        self.hrnet_coords_are_normalized = bool(
            configs.get("hrnet_coords_are_normalized", False)
        )
        self.face_expand_ratio = float(configs.get("face_expand_ratio", 1.25))
        self.eye_select_mode = str(configs.get("eye_select_mode", "confidence"))
        self.eye_score_gap_thresh = float(configs.get("eye_score_gap_thresh", 0.05))

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

    @staticmethod
    def compute_eye_ear(eye_points):
        """
        Compute EAR (Eye Aspect Ratio) for an eye with 8 landmark points.

        WFLW eye layout (8 points per eye):
            0 ─── 1 ─── 2
            │           │
            7           3
            │           │
            6 ─── 5 ─── 4

        EAR = (|p1-p5| + |p2-p4|) / (2 * |p0-p3|)
        Normal open eye: EAR ≈ 0.25-0.35
        Closed/occluded eye: EAR ≈ 0 or abnormal
        """
        if eye_points is None or len(eye_points) < 8:
            return None

        p0 = eye_points[0]
        p1 = eye_points[1]
        p2 = eye_points[2]
        p3 = eye_points[3]
        p4 = eye_points[4]
        p5 = eye_points[5]
        p6 = eye_points[6]
        p7 = eye_points[7]

        w = float(np.linalg.norm(p3 - p7))
        if w < 1e-6:
            return None

        h1 = float(np.linalg.norm(p1 - p5))
        h2 = float(np.linalg.norm(p2 - p4))

        ear = (h1 + h2) / (2.0 * w)
        return ear

    def _select_eye(self, landmarks, frame_shape):
        """
        Fallback eye selection by head pose yaw.

        Note:
            Keep the same convention as the previous version:
                yaw > 0  -> right eye
                yaw <= 0 -> left eye

        If your old version used the opposite convention, swap the two branches.
        """
        head_pose = self.head_pose_estimator.estimate(landmarks, frame_shape)
        yaw = head_pose["yaw"]

        selected_eye = "right" if yaw > 0 else "left"

        return selected_eye, head_pose

    def _select_eye_by_confidence(self, landmarks, landmark_scores, frame_shape):
        """
        Select eye by HRNet landmark confidence.

        Priority:
            1. If confidence scores are available and the score gap is large enough,
            select the eye with higher average confidence.
            2. If scores are unavailable or score gap is too small,
            fall back to yaw-based eye selection.
        """
        score_info = {
            "left_eye_score": None,
            "right_eye_score": None,
            "score_gap": None,
            "reason": None,
        }

        if landmark_scores is None:
            selected_eye, head_pose = self._select_eye(landmarks, frame_shape)
            score_info["reason"] = "fallback_yaw_no_scores"
            return selected_eye, head_pose, score_info

        landmark_scores = np.asarray(landmark_scores, dtype=np.float32)

        if landmark_scores.ndim == 2:
            landmark_scores = landmark_scores[0]

        left_indices = self.eye_indices["left"]
        right_indices = self.eye_indices["right"]

        left_scores = landmark_scores[left_indices]
        right_scores = landmark_scores[right_indices]

        left_score = float(np.mean(left_scores))
        right_score = float(np.mean(right_scores))
        score_gap = abs(left_score - right_score)

        score_info["left_eye_score"] = left_score
        score_info["right_eye_score"] = right_score
        score_info["score_gap"] = score_gap

        if score_gap < self.eye_score_gap_thresh:
            selected_eye, head_pose = self._select_eye(landmarks, frame_shape)
            score_info["reason"] = "fallback_yaw_score_gap_small"
            return selected_eye, head_pose, score_info

        selected_eye = "left" if left_score >= right_score else "right"
        head_pose = None
        score_info["reason"] = "confidence"

        return selected_eye, head_pose, score_info

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
            landmarks, crop_box, landmark_scores = self.landmarker.infer(frame, face_bbox)
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
            if self.eye_select_mode == "confidence":
                selected_eye, head_pose, score_info = self._select_eye_by_confidence(
                    landmarks,
                    landmark_scores,
                    frame.shape,
                )
            elif self.eye_select_mode == "yaw":
                selected_eye, head_pose = self._select_eye(landmarks, frame.shape)
                score_info = {
                    "left_eye_score": None,
                    "right_eye_score": None,
                    "score_gap": None,
                    "reason": "yaw",
                }
            else:
                selected_eye, head_pose, score_info = self._select_eye_by_confidence(
                    landmarks,
                    landmark_scores,
                    frame.shape,
                )

        except Exception as exc:
            return self._return_data(debug_info=f"eye selection error: {exc}")

        selected_points = left_eye_points if selected_eye == "left" else right_eye_points
        eye_bbox = Helper.points_to_bbox(selected_points, frame.shape, padding=self.eye_padding)
        t2 = time.perf_counter()

        debug_info = (
            f"select {selected_eye} eye: "
            f"reason={score_info.get('reason')}, "
            f"left_score={score_info.get('left_eye_score')}, "
            f"right_score={score_info.get('right_eye_score')}, "
            f"score_gap={score_info.get('score_gap')}, "
            f"det_ms={(t1 - t0) * 1000.0:.1f}, "
            f"lmk_ms={(t2 - t1) * 1000.0:.1f}, "
            f"total_ms={(t2 - t0) * 1000.0:.1f}"
        )

        if head_pose is not None:
            debug_info += (
                f", yaw:{head_pose['yaw']:.3f}, "
                f"pitch:{head_pose['pitch']:.3f}, "
                f"roll:{head_pose['roll']:.3f}"
            )
        if crop_box is not None:
            debug_info += f", crop_box={list(map(int, crop_box))}"

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
