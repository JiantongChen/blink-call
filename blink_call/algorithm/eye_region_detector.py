import time
import numpy as np

from insightface.app import FaceAnalysis


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
            "bbox_xyxy": [x1, y1, x2, y2] or None,
            "debug_info": str
        }
    """

    def __init__(self, configs):
        self.ctx_id = configs.get("ctx_id", -1)   # 默认 CPU
        self.det_size = tuple(configs.get("det_size", (640, 640)))
        self.det_thresh = float(configs.get("det_thresh", 0.5))
        self.eye_padding = int(configs.get("eye_padding", 20))
        self.max_num_faces = int(configs.get("max_num_faces", 1))

        self.app = FaceAnalysis(allowed_modules=["detection", "landmark_2d_106"])
        self.app.prepare(
            ctx_id=self.ctx_id,
            det_size=self.det_size,
            det_thresh=self.det_thresh
        )

        self.eye_indices = self._get_eye_indices()

    def _get_eye_indices(self):
        """
        Commonly used InsightFace 106-point eye index groups.

        If visualization shows left/right swapped in your actual dataset,
        just exchange these two index groups.
        """
        left_eye = list(range(87, 97))
        right_eye = list(range(33, 43))
        return {"left": left_eye, "right": right_eye}

    def _largest_face(self, faces):
        """Select the largest detected face."""
        if not faces:
            return None

        def area(face):
            x1, y1, x2, y2 = face.bbox
            return max(0.0, x2 - x1) * max(0.0, y2 - y1)

        return max(faces, key=area)

    def _points_to_bbox(self, eye_points, frame_shape):
        """
        Convert one eye's landmark points to bbox with padding.
        """
        h, w = frame_shape[:2]

        x_min = int(np.floor(np.min(eye_points[:, 0]))) - self.eye_padding
        y_min = int(np.floor(np.min(eye_points[:, 1]))) - self.eye_padding
        x_max = int(np.ceil(np.max(eye_points[:, 0]))) + self.eye_padding
        y_max = int(np.ceil(np.max(eye_points[:, 1]))) + self.eye_padding

        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(w - 1, x_max)
        y_max = min(h - 1, y_max)

        return [x_min, y_min, x_max, y_max]

    def _polygon_area(self, pts):
        """
        Polygon area using shoelace formula.
        Used only as a weak geometric cue.
        """
        if pts is None or len(pts) < 3:
            return 0.0
        x = pts[:, 0]
        y = pts[:, 1]
        return 0.5 * abs(np.dot(x, np.roll(y, -1)) - np.dot(y, np.roll(x, -1)))

    def _polyline_perimeter(self, pts):
        """
        Perimeter of eye contour points.
        """
        if pts is None or len(pts) < 2:
            return 0.0
        shifted = np.roll(pts, -1, axis=0)
        d = np.linalg.norm(pts - shifted, axis=1)
        return float(np.sum(d))

    def _eye_geom_score(self, eye_points, frame_shape):
        """
        Geometry-based quality score for one eye.

        Main idea:
            We want to choose the eye that looks more complete / stable / visible.

        We mainly use:
            - width: visible eye usually keeps a reasonable horizontal span
            - perimeter: more complete contour tends to have a more stable perimeter
            - border distance: eye too close to image edge may be truncated
            - height: used only as a weak cue (important: do NOT make this dominant,
                      because in blink scenarios a closed eye can still be valid)

        Higher score = more reliable eye candidate.
        """
        h, w = frame_shape[:2]

        xs = eye_points[:, 0]
        ys = eye_points[:, 1]

        width = float(np.max(xs) - np.min(xs))
        height = float(np.max(ys) - np.min(ys))
        perimeter = self._polyline_perimeter(eye_points)
        area = self._polygon_area(eye_points)

        cx = float(np.mean(xs))
        cy = float(np.mean(ys))
        border_dist = min(cx, w - 1 - cx, cy, h - 1 - cy)

        # Blink-aware score:
        # width/perimeter are more important than height/area
        score = (
            1.0 * width +
            0.08 * perimeter +
            0.03 * border_dist +
            0.10 * height +
            0.005 * area
        )
        return float(score)

    def _yaw_bias(self, landmarks):
        """
        Estimate weak head-yaw bias from nose position relative to eye midpoint.

        Intuition:
            - If nose shifts toward one eye in 2D projection,
              that side is often more visible in side-face conditions.
            - This is only a weak auxiliary signal, not the main decision.

        Returns:
            yaw_ratio: normalized horizontal bias
        """
        left_eye_points = landmarks[self.eye_indices["left"]]
        right_eye_points = landmarks[self.eye_indices["right"]]

        # Nose region in common 106-point grouping
        nose_points = landmarks[72:87]

        left_center = np.mean(left_eye_points, axis=0)
        right_center = np.mean(right_eye_points, axis=0)
        eye_mid = (left_center + right_center) / 2.0
        nose_center = np.mean(nose_points, axis=0)

        eye_dist = abs(right_center[0] - left_center[0]) + 1e-6
        yaw_ratio = (nose_center[0] - eye_mid[0]) / eye_dist
        return float(yaw_ratio)

    def _select_eye(self, landmarks, frame_shape):
        """
        Select the more reliable eye between left and right.

        Decision rule:
            1. Compute geometry quality score for both eyes
            2. Add a weak yaw-based bonus
            3. Return selected eye bbox
        """
        left_eye_points = landmarks[self.eye_indices["left"]]
        right_eye_points = landmarks[self.eye_indices["right"]]

        left_bbox = self._points_to_bbox(left_eye_points, frame_shape)
        right_bbox = self._points_to_bbox(right_eye_points, frame_shape)

        left_score = self._eye_geom_score(left_eye_points, frame_shape)
        right_score = self._eye_geom_score(right_eye_points, frame_shape)

        # Weak yaw bias
        yaw_ratio = self._yaw_bias(landmarks)
        yaw_thresh = 0.08
        yaw_bonus = 0.12 * max(left_score, right_score)

        if yaw_ratio < -yaw_thresh:
            # Nose is shifted toward left eye side
            left_score += yaw_bonus
        elif yaw_ratio > yaw_thresh:
            # Nose is shifted toward right eye side
            right_score += yaw_bonus

        if left_score >= right_score:
            return left_bbox, "left", left_score, right_score, yaw_ratio
        else:
            return right_bbox, "right", left_score, right_score, yaw_ratio

    def detect(self, frame):
        """
        Detect the most reliable visible eye region from one frame.
        """
        timestamp_ms = int(time.time() * 1000)

        if frame is None:
            return {
                "timestamp_ms": timestamp_ms,
                "bbox_xyxy": None,
                "debug_info": "no_frame"
            }

        if not isinstance(frame, np.ndarray) or frame.ndim < 2:
            return {
                "timestamp_ms": timestamp_ms,
                "bbox_xyxy": None,
                "debug_info": "invalid_frame"
            }

        try:
            faces = self.app.get(frame, max_num=self.max_num_faces)
        except Exception as e:
            return {
                "timestamp_ms": timestamp_ms,
                "bbox_xyxy": None,
                "debug_info": f"inference_error: {str(e)}"
            }

        if len(faces) == 0:
            return {
                "timestamp_ms": timestamp_ms,
                "bbox_xyxy": None,
                "debug_info": "no_face_detected"
            }

        face = self._largest_face(faces)
        landmarks = getattr(face, "landmark_2d_106", None)

        if landmarks is None:
            return {
                "timestamp_ms": timestamp_ms,
                "bbox_xyxy": None,
                "debug_info": "no_landmark"
            }

        landmarks = np.asarray(landmarks)

        bbox, selected_eye, left_score, right_score, yaw_ratio = self._select_eye(
            landmarks, frame.shape
        )

        return {
            "timestamp_ms": timestamp_ms,
            "bbox_xyxy": bbox,
            "debug_info": (
                f"ok_landmark106_selected_{selected_eye}_eye"
                f"_ls_{left_score:.3f}_rs_{right_score:.3f}"
                f"_yaw_{yaw_ratio:.3f}_face_count_{len(faces)}"
            )
        }