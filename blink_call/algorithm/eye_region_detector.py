import time
from pathlib import Path

import numpy as np
from insightface.app import FaceAnalysis
from PySide6.QtCore import QStandardPaths

from blink_call.utils.head_pose_estimator import InsightFaceHeadPose
from blink_call.utils.helper import Helper

INSIGHT_FACE_ROOT_PATH = (
    Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    / "blink_call"
    / "blink_call_model_files"
    / "insightface"
)


class EyeRegionDetector:
    """
    Eye-region detection using InsightFace landmark model.

    Pipeline:
        1. Detect face
        2. Predict 106 facial landmarks
        3. Compute left-eye and right-eye candidates
        4. Select the more reliable eye
        5. Return ONE bbox_xyxy

    Return format:
        {
            "timestamp_ms": int,
            "eye_bbox_xyxy": [x1, y1, x2, y2] or None,
            "face_bbox_xyxy": [x1, y1, x2, y2] or None,
            "landmarks": [[x1, y1], [x2, y2] ... [x106, y106]] or None,
            "debug_info": str
        }
    """

    def __init__(self, configs):
        self.ctx_id = configs.get("ctx_id", -1)
        self.det_size = tuple(configs.get("det_size", (320, 320)))
        self.det_thresh = float(configs.get("det_thresh", 0.5))
        self.eye_padding = int(configs.get("eye_padding", 20))
        self.max_num_faces = int(configs.get("max_num_faces", 1))

        self.app = FaceAnalysis(
            name="buffalo_s_sft",
            root=str(INSIGHT_FACE_ROOT_PATH.resolve()),
            allowed_modules=["detection", "landmark_2d_106"],
        )
        self.app.prepare(ctx_id=self.ctx_id, det_size=self.det_size, det_thresh=self.det_thresh)

        # https://github.com/nttstar/insightface-resources/blob/master/alignment/images/2d106markup.jpg
        self.eye_indices = {"left": list(range(87, 97)), "right": list(range(33, 43))}
        self.head_pose_estimator = InsightFaceHeadPose()

    def detect(self, frame):
        """
        Detect the most reliable visible eye region from one frame.
        """
        if frame is None:
            return self._return_data(debug_info="frame is None")

        if not isinstance(frame, np.ndarray) or frame.ndim < 2:
            return self._return_data(debug_info="invalid frame data")

        started = time.perf_counter()
        try:
            faces = self.app.get(frame, max_num=1)
        except Exception as exc:
            return self._return_data(debug_info=f"insightface inference error: {str(exc)}")

        if len(faces) == 0:
            return self._return_data(debug_info="no face detected")

        landmarks = getattr(faces[0], "landmark_2d_106", None)
        if landmarks is None:
            return self._return_data(debug_info="no landmark_2d_106 detected")

        head_pose = self.head_pose_estimator.estimate(landmarks, frame.shape)
        selected_eye = "left" if head_pose["yaw"] > 0 else "right"
        selected_eye_points = landmarks[self.eye_indices.get(selected_eye)]
        eye_bbox = Helper.points_to_bbox(selected_eye_points, frame.shape, self.eye_padding)
        elapsed_ms = (time.perf_counter() - started) * 1000.0

        return self._return_data(
            eye_bbox_xyxy=eye_bbox,
            face_bbox_xyxy=faces[0]["bbox"].tolist(),
            landmarks=landmarks.tolist(),
            debug_info=(
                f"select {selected_eye} eye: elapsed_ms={elapsed_ms:.1f}, yaw:{head_pose['yaw']:.3f}, pitch:{head_pose['pitch']:.3f}, roll:{head_pose['roll']:.3f}"
            ),
        )

    def _return_data(self, eye_bbox_xyxy=None, face_bbox_xyxy=None, landmarks=None, debug_info=""):
        return {
            "timestamp_ms": int(time.time() * 1000),
            "eye_bbox_xyxy": eye_bbox_xyxy,
            "face_bbox_xyxy": face_bbox_xyxy,
            "landmarks": landmarks,
            "debug_info": debug_info,
        }
