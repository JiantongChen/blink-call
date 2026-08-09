import hashlib
import threading
import time
from collections import deque
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from blink_call.algorithm import EyeRegionDetector, EyeStateClassifier
from blink_call.utils.helper import Helper


class InferenceWorker(QThread):
    result_ready = Signal(dict)
    show_debug_msg = Signal(str)
    eye_region_status = Signal(str)

    def __init__(self, home_model):
        super().__init__()
        self.home_model = home_model
        self._debug_frame_lock = threading.Lock()
        self._debug_frame_buffer = deque(maxlen=3)

    def initialize_vars(self, config, include_debug_frame=False):
        self.blink_pattern = config["pattern"]
        self.include_debug_frame = bool(include_debug_frame)
        with self._debug_frame_lock:
            self._debug_frame_buffer.clear()
        self.debug_info(f"[InferenceWorker] blink_pattern: {self.blink_pattern}")

        self.eye_region_detector = EyeRegionDetector(config["eye_region_detection_algorithm"])
        classifier_config = config["eye_state_classification_algorithm"] or {}
        self.eye_state_classifier = EyeStateClassifier(classifier_config)
        self.classifier_input_roi_scale = float(
            classifier_config.get("classifier_input_roi_scale", 1.5)
        )
        if self.classifier_input_roi_scale < 1.0:
            raise ValueError("classifier_input_roi_scale must be >= 1.0")
        self.model_identity = self.collect_model_identity()

        self.running = True
        self.min_interval = 1.0 / 10.0
        self.last_time = 0.0

        self.stat_fps_interval = 10.0
        self.infer_fps_window_start = time.perf_counter()
        self.infer_fps_counter = 0

        self.latest_eye_bbox = None
        self.latest_face_bbox = None
        self.latest_landmarks = None
        self.debug_emit_interval_s = 1.0
        self.last_eye_region_debug_emit_s = time.perf_counter()
        self.last_eye_state_debug_emit_s = time.perf_counter()

        self.match_cooldown_s = 1.0
        self.last_match_time = -1.0

        self.progress_step_idx = 0
        self.progress_in_step_s = 0.0
        self.last_progress_update_s = None
        self.transition_buffer_s = 3.0
        self.in_transition_buffer = False
        self.transition_elapsed_s = 0.0

        self.valid_eye_states = ("open", "closed")
        self.state_hold_s = 0.45
        self.state_vote_window_size = 5
        self.state_vote_min_count = 3
        self.state_vote_window = []
        self.last_stable_eye_state = None
        self.last_stable_eye_state_s = 0.0

    @staticmethod
    def file_sha256(path, chunk_size=1024 * 1024):
        digest = hashlib.sha256()
        with Path(path).open("rb") as handle:
            while chunk := handle.read(chunk_size):
                digest.update(chunk)
        return digest.hexdigest()

    def collect_model_identity(self):
        """Hash the exact detector/landmarker files opened by this worker."""
        identities = {}
        model_paths = {
            "yolov6": getattr(self.eye_region_detector, "yolov6_onnx_path", None),
            "hrnet": getattr(self.eye_region_detector, "hrnet_onnx_path", None),
        }
        for name, raw_path in model_paths.items():
            if not raw_path:
                continue
            path = Path(raw_path).resolve()
            try:
                identity = {
                    "path": str(path),
                    "size_bytes": path.stat().st_size,
                    "sha256": self.file_sha256(path),
                }
                identities[name] = identity
                self.debug_info(
                    f"[InferenceWorker] {name}_model: path={identity['path']}, "
                    f"size_bytes={identity['size_bytes']}, sha256={identity['sha256']}"
                )
            except Exception as exc:
                identities[name] = {"path": str(path), "error": str(exc)}
                self.debug_info(f"[InferenceWorker] {name}_model_identity_error: path={path}, error={exc}")
        return identities

    def _store_debug_frame(self, timestamp_ms, frame):
        if not self.include_debug_frame:
            return
        with self._debug_frame_lock:
            self._debug_frame_buffer.append((int(timestamp_ms), frame))

    def get_debug_frame(self, timestamp_ms):
        """Return a matching debug frame without sending it through Qt signals."""
        with self._debug_frame_lock:
            for buffered_timestamp_ms, frame in reversed(self._debug_frame_buffer):
                if buffered_timestamp_ms == int(timestamp_ms):
                    return frame
        return None

    def reset_progress_state(self):
        self.progress_step_idx = 0
        self.progress_in_step_s = 0.0
        self.in_transition_buffer = False
        self.transition_elapsed_s = 0.0

    def debug_info(self, text, source=""):
        now = time.perf_counter()

        if source == "eye_region":
            if now - self.last_eye_region_debug_emit_s >= self.debug_emit_interval_s:
                self.last_eye_region_debug_emit_s = now
                self.show_debug_msg.emit(text)

        elif source == "eye_state":
            if now - self.last_eye_state_debug_emit_s >= self.debug_emit_interval_s:
                self.last_eye_state_debug_emit_s = now
                self.show_debug_msg.emit(text)

        else:
            self.show_debug_msg.emit(text)

    def stat_fps(self):
        self.infer_fps_counter += 1

        now = time.perf_counter()
        elapsed = now - self.infer_fps_window_start

        if elapsed >= self.stat_fps_interval:
            infer_fps = self.infer_fps_counter / elapsed
            self.debug_info(f"[InferenceWorker] inference_fps: {infer_fps:.2f}")

            self.infer_fps_window_start = now
            self.infer_fps_counter = 0

    def stop(self):
        self.running = False

    def run(self):
        while self.running:
            now = time.perf_counter()
            if now - self.last_time < self.min_interval:
                time.sleep(self.min_interval / 10.0)
                continue
            self.last_time = now

            frame = self.home_model.read_frame()[1]
            if frame is None:
                self.debug_info("[InferenceWorker] WARNING: frame is None")
                continue

            # ``read_frame`` returns a snapshot.  Keep its read timestamp with
            # the result so that detector, landmarker and classifier activity
            # can be traced back to this exact source frame.
            source_timestamp_ms = int(time.time() * 1000)
            result = self.inference(frame, source_timestamp_ms=source_timestamp_ms)
            if not self.running:
                break
            self.result_ready.emit(result)
            self.stat_fps()

    def inference(self, frame, source_timestamp_ms=None):
        """Run the complete eye pipeline synchronously on one frame snapshot.

        This method already executes inside ``InferenceWorker``'s ``QThread``.
        Keeping face/landmark detection and eye classification here avoids the
        old one-frame (or more) lag caused by a second executor and guarantees
        that the eye crop is taken from the same frame used to locate it.
        """
        if source_timestamp_ms is None:
            source_timestamp_ms = int(time.time() * 1000)
        inference_started_timestamp_ms = int(time.time() * 1000)
        inference_started = time.perf_counter()

        detection_started = time.perf_counter()
        self.detect_eye_region(frame)
        detection_elapsed_ms = (time.perf_counter() - detection_started) * 1000.0

        detector_eye_bbox = self.latest_eye_bbox
        classifier_eye_bbox = self._get_classifier_input_bbox(
            frame.shape,
            detector_eye_bbox,
            self.classifier_input_roi_scale,
        )
        eye_roi = Helper.image_cropping(frame, classifier_eye_bbox)
        classification_started = time.perf_counter()
        cls_result = self.eye_state_classifier.classify(
            eye_roi,
            debug_context={
                "eye_bbox_xyxy": classifier_eye_bbox,
                "detector_eye_bbox_xyxy": detector_eye_bbox,
                "face_bbox_xyxy": self.latest_face_bbox,
                "frame_shape": list(frame.shape),
                "classifier_input_roi_scale": self.classifier_input_roi_scale,
            },
        )
        classification_elapsed_ms = (time.perf_counter() - classification_started) * 1000.0
        self.debug_info(f"[EyeStateClassifier] debug info: {cls_result.get('debug_info', '')}", "eye_state")

        raw_eye_state = cls_result.get("state")
        eye_state = self.stabilize_eye_state(raw_eye_state)
        confidence = cls_result.get("confidence")
        progress_ratio, blinck_call_flag, stage_sound_prompt_flag = self.update_forward_progress(eye_state)
        inference_elapsed_ms = (time.perf_counter() - inference_started) * 1000.0
        inference_finished_timestamp_ms = int(time.time() * 1000)
        confidence_text = "None" if confidence is None else f"{float(confidence):.3f}"

        result = {
            "timestamp_ms": inference_finished_timestamp_ms,
            "source_timestamp_ms": int(source_timestamp_ms),
            "inference_started_timestamp_ms": inference_started_timestamp_ms,
            "inference_finished_timestamp_ms": inference_finished_timestamp_ms,
            "inference_elapsed_ms": float(inference_elapsed_ms),
            "debug_detection_elapsed_ms": float(detection_elapsed_ms),
            "debug_classification_elapsed_ms": float(classification_elapsed_ms),
            "blinck_call_flag": bool(blinck_call_flag),
            "stage_sound_prompt_flag": bool(stage_sound_prompt_flag),
            "blink_progress_ratio": float(progress_ratio),
            "debug_eye_bbox_xyxy": classifier_eye_bbox,
            "debug_detector_eye_bbox_xyxy": detector_eye_bbox,
            "debug_face_bbox_xyxy": self.latest_face_bbox,
            "debug_landmarks": self.latest_landmarks,
            "debug_model_identity": self.model_identity,
            "debug_info": "\n".join(
                [
                    "frame_pipeline: same_frame",
                    f"source_timestamp_ms: {int(source_timestamp_ms)}",
                    f"inference_started_timestamp_ms: {inference_started_timestamp_ms}",
                    f"inference_elapsed_ms: {inference_elapsed_ms:.1f}",
                    f"detection_elapsed_ms: {detection_elapsed_ms:.1f}",
                    f"classification_elapsed_ms: {classification_elapsed_ms:.1f}",
                    f"eye_state: {eye_state}",
                    f"raw_eye_state: {raw_eye_state}",
                    f"confidence: {confidence_text}",
                    f"pattern_progress: {progress_ratio:.3f}",
                    f"detector_eye_bbox: {detector_eye_bbox}",
                    f"classifier_eye_bbox: {classifier_eye_bbox}",
                    f"classifier_input_roi_scale: {self.classifier_input_roi_scale:.2f}",
                ]
            ),
        }
        # Keep the large image out of the queued Qt result signal.  The UI can
        # retrieve the matching frame from this bounded cache by timestamp.
        self._store_debug_frame(inference_finished_timestamp_ms, frame)
        return result

    @staticmethod
    def _get_classifier_input_bbox(frame_shape, eye_bbox, roi_scale):
        """Return a natural square ROI expanded around the detector eye box."""
        if eye_bbox is None or roi_scale is None:
            return eye_bbox

        height, width = frame_shape[:2]
        x1, y1, x2, y2 = map(float, eye_bbox)
        bbox_width = max(2.0, x2 - x1)
        bbox_height = max(2.0, y2 - y1)
        side = int(round(max(bbox_width, bbox_height) * float(roi_scale)))
        side = min(max(2, side), max(2, min(width - 1, height - 1)))

        center_x = 0.5 * (x1 + x2)
        center_y = 0.5 * (y1 + y2)
        left = int(round(center_x - 0.5 * side))
        top = int(round(center_y - 0.5 * side))
        right = left + side
        bottom = top + side

        if left < 0:
            right -= left
            left = 0
        if top < 0:
            bottom -= top
            top = 0
        if right >= width:
            left -= right - (width - 1)
            right = width - 1
        if bottom >= height:
            top -= bottom - (height - 1)
            bottom = height - 1

        left = max(0, left)
        top = max(0, top)
        return [left, top, max(left + 2, right), max(top + 2, bottom)]

    def detect_eye_region(self, frame):
        """Update regions from ``frame`` and clear stale results on failure."""
        try:
            result = self.eye_region_detector.detect(frame) or {}
        except Exception as exc:
            self.latest_eye_bbox = None
            self.latest_face_bbox = None
            self.latest_landmarks = None
            self.eye_region_status.emit("error")
            self.debug_info(f"[EyeRegionDetector] eye_region_error: {exc}")
            return

        eye_bbox = result.get("eye_bbox_xyxy")
        face_bbox = result.get("face_bbox_xyxy")
        landmarks = result.get("landmarks")
        self.latest_eye_bbox = [int(v) for v in eye_bbox] if eye_bbox is not None and len(eye_bbox) else None
        self.latest_face_bbox = [int(v) for v in face_bbox] if face_bbox is not None and len(face_bbox) else None
        self.latest_landmarks = (
            [[int(point[0]), int(point[1])] for point in landmarks]
            if landmarks is not None and len(landmarks)
            else None
        )
        if not self.latest_face_bbox:
            status = "no_face"
        elif not self.latest_landmarks:
            status = "landmarks_error"
        else:
            status = "ok" if self.latest_eye_bbox else "error"
        self.eye_region_status.emit(status)
        self.debug_info(f"[EyeRegionDetector] debug info: {result.get('debug_info', '')}", "eye_region")

    def stabilize_eye_state(self, raw_eye_state):
        if hasattr(raw_eye_state, "value"):
            normalized_state = raw_eye_state.value
        elif raw_eye_state is None:
            normalized_state = None
        else:
            normalized_state = str(raw_eye_state)

        now = time.perf_counter()
        if normalized_state in self.valid_eye_states:
            self.state_vote_window.append(normalized_state)
            self.state_vote_window = self.state_vote_window[-self.state_vote_window_size :]

            voted_state = max(self.valid_eye_states, key=self.state_vote_window.count)
            if self.state_vote_window.count(voted_state) >= self.state_vote_min_count:
                self.last_stable_eye_state = voted_state
                self.last_stable_eye_state_s = now
                return voted_state

            if self.last_stable_eye_state and now - self.last_stable_eye_state_s <= self.state_hold_s:
                return self.last_stable_eye_state
            return normalized_state

        if self.last_stable_eye_state and now - self.last_stable_eye_state_s <= self.state_hold_s:
            return self.last_stable_eye_state

        return normalized_state

    def update_forward_progress(self, eye_state):
        now = time.perf_counter()
        dt = 0.0 if self.last_progress_update_s is None else min(now - self.last_progress_update_s, 0.5)
        self.last_progress_update_s = now
        stage_sound_prompt_flag = False

        if self.in_transition_buffer:
            self.transition_elapsed_s += dt

            if self.transition_elapsed_s > self.transition_buffer_s:
                self.reset_progress_state()
            elif eye_state in {"open", "closed"} and self.progress_step_idx < len(self.blink_pattern):
                next_rule_state = self.blink_pattern[self.progress_step_idx]["state"]
                if eye_state == next_rule_state:
                    self.in_transition_buffer = False
                    self.transition_elapsed_s = 0.0
                    self.progress_in_step_s = dt

        elif eye_state in {"open", "closed"} and self.progress_step_idx < len(self.blink_pattern):
            rule = self.blink_pattern[self.progress_step_idx]
            rule_state = rule["state"]
            rule_duration = float(rule["duration_s"])

            if eye_state == rule_state:
                self.progress_in_step_s += dt
            else:
                self.reset_progress_state()

            if self.progress_in_step_s >= rule_duration:
                if bool(rule.get("sound_prompt")):
                    stage_sound_prompt_flag = True
                self.progress_step_idx += 1

                overflow = self.progress_in_step_s - rule_duration
                is_same_state = (
                    self.progress_step_idx < len(self.blink_pattern)
                    and eye_state == self.blink_pattern[self.progress_step_idx]["state"]
                )
                if is_same_state:
                    self.progress_in_step_s = overflow
                else:
                    self.progress_in_step_s = 0.0
                    if self.progress_step_idx < len(self.blink_pattern):
                        self.in_transition_buffer = True
                        self.transition_elapsed_s = 0.0

        ratio = self.current_progress_ratio(self.blink_pattern)

        blink = False
        if ratio >= 1.0 and (now - self.last_match_time) >= self.match_cooldown_s:
            blink = True
            self.last_match_time = now
            self.reset_progress_state()

        return ratio, blink, stage_sound_prompt_flag

    def current_progress_ratio(self, pattern):
        if self.progress_step_idx >= len(pattern):
            return 1.0

        total = sum(float(item["duration_s"]) for item in pattern)

        completed = 0.0
        for idx in range(self.progress_step_idx):
            completed += float(pattern[idx]["duration_s"])

        return min(1.0, max(0.0, (completed + self.progress_in_step_s) / total))
