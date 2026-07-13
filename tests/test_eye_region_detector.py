import unittest

import numpy as np

from blink_call.algorithm.eye_region_detector import EyeRegionDetector


class FakeFaceDetector:
    def __init__(self, results):
        self.results = list(results)
        self.calls = []
        self.last_debug_info = "fake detector"

    def detect(self, image):
        self.calls.append(image.shape[:2])
        faces = self.results.pop(0)
        return (
            np.asarray(faces, dtype=np.float32),
            np.zeros((0, 0, 2), dtype=np.float32),
        )


class FakeLandmarker:
    def __init__(self):
        self.face_boxes = []

    def infer(self, frame, face_bbox):
        self.face_boxes.append(face_bbox)
        landmarks = np.tile(np.array([[80.0, 45.0]], dtype=np.float32), (98, 1))
        landmarks[:33, 0] = np.linspace(65.0, 95.0, 33)
        landmarks[:33, 1] = np.linspace(35.0, 65.0, 33)
        landmarks[60:68] = np.array(
            [
                [72, 43],
                [74, 42],
                [76, 42],
                [78, 43],
                [76, 44],
                [74, 44],
                [73, 43],
                [77, 43],
            ],
            dtype=np.float32,
        )
        landmarks[68:76] = landmarks[60:68] + np.array([12, 0], dtype=np.float32)
        scores = np.ones((98,), dtype=np.float32)
        return landmarks, (0, 0, frame.shape[1], frame.shape[0]), scores


def make_detector(face_results, last_face_bbox=None):
    detector = EyeRegionDetector.__new__(EyeRegionDetector)
    detector.face_detector = FakeFaceDetector(face_results)
    detector.landmarker = FakeLandmarker()
    detector.eye_indices = {
        "left": list(range(68, 76)),
        "right": list(range(60, 68)),
    }
    detector.eye_padding = 20
    detector.eye_padding_ratio = 0.06
    detector.min_eye_padding = 4
    detector.tracking_roi_scale = 2.0
    detector.fallback_crop_ratio = 0.5
    detector.last_face_bbox = last_face_bbox
    return detector


class EyeRegionDetectorTest(unittest.TestCase):
    def setUp(self):
        self.frame = np.zeros((100, 200, 3), dtype=np.uint8)

    def test_center_zoom_fallback_maps_detection_to_frame_coordinates(self):
        detector = make_detector(
            [
                np.zeros((0, 5), dtype=np.float32),
                [[10, 5, 50, 45, 0.8]],
            ]
        )

        result = detector.detect(self.frame)

        self.assertEqual(detector.face_detector.calls, [(100, 200), (50, 100)])
        self.assertEqual(detector.landmarker.face_boxes[0], [60.0, 30.0, 100.0, 70.0])
        self.assertEqual(result["face_bbox_xyxy"], [60.0, 30.0, 100.0, 70.0])
        self.assertIn("mode=center_zoom", result["debug_info"])
        self.assertIsNotNone(result["eye_bbox_xyxy"])

    def test_previous_face_uses_zoomed_tracking_roi_first(self):
        detector = make_detector(
            [[[10, 10, 30, 40, 0.9]]],
            last_face_bbox=[80, 30, 120, 70],
        )

        result = detector.detect(self.frame)

        self.assertEqual(detector.face_detector.calls, [(80, 80)])
        self.assertEqual(detector.landmarker.face_boxes[0], [70.0, 20.0, 90.0, 50.0])
        self.assertEqual(result["face_bbox_xyxy"], [70.0, 20.0, 90.0, 50.0])
        self.assertIn("mode=tracking_roi", result["debug_info"])

    def test_eye_padding_shrinks_for_a_small_face(self):
        detector = make_detector([[[60, 25, 105, 75, 0.9]]])

        result = detector.detect(self.frame)

        self.assertIn("eye_padding=4", result["debug_info"])


if __name__ == "__main__":
    unittest.main()
