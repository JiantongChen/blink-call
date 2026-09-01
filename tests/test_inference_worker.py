import unittest
from concurrent.futures import Future

import numpy as np

from blink_call.core.inference_worker import InferenceWorker


class RecordingClassifier:
    def __init__(self, state="open"):
        self.state = state
        self.rois = []

    def classify(self, eye_roi, debug_context=None):
        self.rois.append(eye_roi)
        return {
            "state": self.state,
            "confidence": 1.0,
            "debug_info": "fake classifier",
        }


class PendingExecutor:
    def __init__(self):
        self.submit_count = 0
        self.future = Future()
        self.shutdown_calls = []

    def submit(self, fn, *args):
        self.submit_count += 1
        return self.future

    def shutdown(self, wait, cancel_futures):
        self.shutdown_calls.append((wait, cancel_futures))


class ImmediateExecutor:
    def __init__(self):
        self.submit_count = 0
        self.shutdown_calls = []

    def submit(self, fn, *args):
        self.submit_count += 1
        future = Future()
        try:
            future.set_result(fn(*args))
        except Exception as exc:
            future.set_exception(exc)
        return future

    def shutdown(self, wait, cancel_futures):
        self.shutdown_calls.append((wait, cancel_futures))


class FakeDetector:
    def detect(self, frame):
        return {
            "status": "ok",
            "eye_bbox_xyxy": [2, 2, 6, 6],
            "face_bbox_xyxy": [0, 0, 8, 8],
            "landmarks": [[3, 3], [5, 5]],
            "debug_info": "fake detector",
        }


def make_worker(pattern=None):
    worker = InferenceWorker(None)
    worker.blink_pattern = pattern or [{"state": "open", "duration_s": 1.0}]
    worker.match_cooldown_s = 1.0
    worker.last_match_time = -1.0
    worker.progress_step_idx = 0
    worker.progress_in_step_s = 0.0
    worker.transition_buffer_s = 3.0
    worker.in_transition_buffer = False
    worker.transition_deadline_s = None
    worker.valid_eye_states = ("open", "closed")
    worker.state_window_pass_ratio = 0.9
    worker.state_window_start_s = None
    worker.state_window_samples = []
    worker.state_window_debug_info = "state_window=idle"
    worker.last_stable_eye_state = None
    return worker


def configure_inference(worker, executor):
    worker.eye_region_detector = FakeDetector()
    worker.eye_state_classifier = RecordingClassifier()
    worker.classifier_input_roi_scale = 1.0
    worker.model_identity = {}
    worker.latest_eye_bbox = None
    worker.latest_face_bbox = None
    worker.latest_landmarks = None
    worker.latest_eye_region_status = "inference_error"
    worker.latest_eye_region_source_timestamp_ms = None
    worker.latest_eye_region_sample_timestamp_s = None
    worker.latest_detection_elapsed_ms = None
    worker.pending_eye_region_future = None
    worker.eye_region_executor = executor
    worker.debug_emit_interval_s = 1.0
    worker.last_eye_region_debug_emit_s = float("inf")
    worker.last_eye_state_debug_emit_s = float("inf")


class InferenceWorkerTests(unittest.TestCase):
    def test_classifier_keeps_running_while_detector_future_is_pending(self):
        worker = make_worker()
        executor = PendingExecutor()
        configure_inference(worker, executor)
        frame = np.zeros((10, 10, 3), dtype=np.uint8)

        worker.inference(frame, source_timestamp_ms=1000, sample_timestamp_s=0.0)
        worker.inference(frame, source_timestamp_ms=1100, sample_timestamp_s=0.1)

        self.assertEqual(executor.submit_count, 1)
        self.assertEqual(len(worker.eye_state_classifier.rois), 2)
        self.assertIs(worker.pending_eye_region_future, executor.future)

        worker._shutdown_eye_region_executor()
        self.assertEqual(executor.shutdown_calls, [(False, True)])

    def test_completed_detector_result_is_used_without_waiting_for_next_detection(self):
        worker = make_worker()
        executor = ImmediateExecutor()
        configure_inference(worker, executor)
        frame = np.zeros((10, 10, 3), dtype=np.uint8)

        first = worker.inference(
            frame,
            source_timestamp_ms=1000,
            sample_timestamp_s=0.0,
        )
        second = worker.inference(
            frame,
            source_timestamp_ms=1100,
            sample_timestamp_s=0.1,
        )

        self.assertIsNone(worker.eye_state_classifier.rois[0])
        self.assertEqual(worker.eye_state_classifier.rois[1].shape, (4, 4, 3))
        self.assertIsNone(first["debug_eye_region_source_timestamp_ms"])
        self.assertEqual(second["debug_eye_region_source_timestamp_ms"], 1000)
        self.assertEqual(second["debug_detector_eye_bbox_xyxy"], [2, 2, 6, 6])
        self.assertEqual(executor.submit_count, 2)

        worker._shutdown_eye_region_executor()

    def test_state_window_passes_at_exactly_ninety_percent_correct(self):
        worker = make_worker()
        self.assertTrue(worker._start_state_window("open", 0.0))

        for _ in range(8):
            worker._record_state_window_sample("open")
        worker._record_state_window_sample("not_sure")

        passed, window_start_s = worker._finish_state_window()

        self.assertTrue(passed)
        self.assertEqual(window_start_s, 0.0)
        self.assertIn("correct_count=9", worker.state_window_debug_info)
        self.assertIn("not_sure_count=1", worker.state_window_debug_info)
        self.assertIn("correct_ratio=0.900", worker.state_window_debug_info)

    def test_state_window_fails_below_ninety_percent_correct(self):
        worker = make_worker()
        self.assertTrue(worker._start_state_window("open", 0.0))

        for _ in range(7):
            worker._record_state_window_sample("open")
        worker._record_state_window_sample("closed")
        worker._record_state_window_sample("not_sure")

        passed, _ = worker._finish_state_window()

        self.assertFalse(passed)
        self.assertIn("correct_count=8", worker.state_window_debug_info)
        self.assertIn("incorrect_count=1", worker.state_window_debug_info)
        self.assertIn("not_sure_count=1", worker.state_window_debug_info)
        self.assertIn("correct_ratio=0.800", worker.state_window_debug_info)

    def test_unknown_results_are_counted_as_not_sure_votes(self):
        worker = make_worker()
        self.assertTrue(worker._start_state_window("open", 0.0))

        worker._record_state_window_sample(None)
        worker._record_state_window_sample("unknown")
        worker._record_state_window_sample("not_exist")

        self.assertEqual(
            worker.state_window_samples,
            ["correct", "not_sure", "not_sure", "not_sure"],
        )

    def test_sample_at_deadline_is_not_counted_in_finished_window(self):
        worker = make_worker()
        worker.update_forward_progress("open", sample_timestamp_s=0.0)
        for index in range(1, 9):
            worker.update_forward_progress("open", sample_timestamp_s=index / 10)
        worker.update_forward_progress("not_sure", sample_timestamp_s=0.9)

        ratio, blink, _ = worker.update_forward_progress(
            "closed",
            sample_timestamp_s=1.0,
        )

        self.assertEqual(ratio, 1.0)
        self.assertTrue(blink)


if __name__ == "__main__":
    unittest.main()
