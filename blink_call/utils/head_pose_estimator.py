import cv2
import numpy as np


class InsightFaceHeadPose:
    """
    106-landmark based head pose estimator (yaw/pitch/roll)
    using OpenCV solvePnP.
    """

    def __init__(self):
        # 3D canonical face model points: nose, chin, left-eye, right-eye, left-mouth, right-mouth
        self.model_points = np.array(
            [
                (0.0, 0.0, 0.0),
                (0.0, -63.6, -12.5),
                (-43.3, 32.7, -26.0),
                (43.3, 32.7, -26.0),
                (-28.9, -28.9, -24.1),
                (28.9, -28.9, -24.1),
            ],
            dtype=np.float32,
        )

        self.nose_idx = 80
        self.chin_idx = 0
        self.left_eye_idx = 88
        self.right_eye_idx = 38
        self.left_mouth_idx = 61
        self.right_mouth_idx = 52

    def _to_landmark_array(self, lm106):
        lm = np.asarray(lm106, dtype=np.float32)
        if lm.ndim != 2 or lm.shape[1] < 2 or lm.shape[0] < 97:
            raise ValueError("invalid 106 landmarks")
        return lm[:, :2]

    def _get_image_points(self, lm106):
        lm = self._to_landmark_array(lm106)

        nose = lm[self.nose_idx]
        chin = lm[self.chin_idx]
        left_eye = lm[self.left_eye_idx]
        right_eye = lm[self.right_eye_idx]
        left_mouth = lm[self.left_mouth_idx]
        right_mouth = lm[self.right_mouth_idx]

        image_points = np.array([nose, chin, left_eye, right_eye, left_mouth, right_mouth], dtype=np.float32)
        return image_points, left_eye, right_eye, nose

    def estimate(self, lm106, image_shape):
        h, w = image_shape[:2]
        if h <= 0 or w <= 0:
            return self._empty_result()

        try:
            image_points, left_eye, right_eye, nose = self._get_image_points(lm106)
        except Exception:
            return self._empty_result()

        focal_length = float(max(w, h))
        center = (w / 2, h / 2)

        camera_matrix = np.array(
            [[focal_length, 0, center[0]], [0, focal_length, center[1]], [0, 0, 1]], dtype=np.float32
        )

        dist_coeffs = np.zeros((4, 1), dtype=np.float32)

        ok, rvec, tvec = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            flags=cv2.SOLVEPNP_EPNP,
        )
        if not ok:
            return self._empty_result()

        ok, rvec, tvec = cv2.solvePnP(
            self.model_points,
            image_points,
            camera_matrix,
            dist_coeffs,
            rvec=rvec,
            tvec=tvec,
            useExtrinsicGuess=True,
            flags=cv2.SOLVEPNP_ITERATIVE,
        )
        if not ok:
            return self._empty_result()

        rmat, _ = cv2.Rodrigues(rvec)
        proj_matrix = np.hstack((rmat, tvec))
        _, _, _, _, _, _, euler = cv2.decomposeProjectionMatrix(proj_matrix)
        pitch, yaw, roll = (float(v) for v in euler.reshape(-1))

        yaw_2d = self._estimate_yaw_2d(left_eye, right_eye, nose)
        if yaw_2d is not None:
            yaw = 0.7 * yaw + 0.3 * yaw_2d

        return {"pitch": pitch, "yaw": yaw, "roll": roll, "rvec": rvec, "tvec": tvec}

    def _estimate_yaw_2d(self, left_eye, right_eye, nose):
        eye_span = float(np.linalg.norm(right_eye - left_eye))
        if eye_span < 1e-6:
            return None

        eye_mid_x = float((left_eye[0] + right_eye[0]) * 0.5)
        dx = float(nose[0]) - eye_mid_x
        ratio = dx / (0.5 * eye_span)
        ratio = float(np.clip(ratio, -1.0, 1.0))
        return ratio * 35.0

    def _empty_result(self):
        return {
            "pitch": 0.0,
            "yaw": 0.0,
            "roll": 0.0,
            "rvec": None,
            "tvec": None,
        }
