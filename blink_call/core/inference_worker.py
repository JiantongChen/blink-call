import time
from concurrent.futures import ThreadPoolExecutor

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

    def initialize_vars(self, config):
        self.blink_pattern = config["pattern"]
        self.debug_info(f"[InferenceWorker] blink_pattern: {self.blink_pattern}")

        self.eye_region_detector = EyeRegionDetector(config["eye_region_detection_algorithm"])
        self.eye_state_classifier = EyeStateClassifier(config["eye_state_classification_algorithm"])

        self.running = True
        self.min_interval = 1.0 / 10.0
        self.last_time = 0.0

        self.stat_fps_interval = 10.0
        self.infer_fps_window_start = time.perf_counter()
        self.infer_fps_counter = 0

        self.latest_eye_bbox = None
        self.latest_face_bbox = None
        self.latest_landmarks = None
        self.pending_bbox_future = None
        self.bbox_executor = None
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

            result = self.inference(frame)
            self.result_ready.emit(result)
            self.stat_fps()

        if self.pending_bbox_future is not None:
            self.pending_bbox_future.cancel()
            self.pending_bbox_future = None

        if self.bbox_executor is not None:
            self.bbox_executor.shutdown(wait=False, cancel_futures=True)
            self.bbox_executor = None

    def inference(self, frame):
        self.poll_latest_bbox()
        self.submit_eye_region_detect_task(frame)

        eye_roi = Helper.image_cropping(frame, self.latest_eye_bbox)
        cls_result = self.eye_state_classifier.classify(eye_roi)
        self.debug_info(f"[EyeStateClassifier] debug info: {cls_result['debug_info']}", "eye_state")

        raw_eye_state = cls_result.get("state")
        eye_state = self.stabilize_eye_state(raw_eye_state)
        confidence = cls_result.get("confidence")
        progress_ratio, blinck_call_flag, stage_sound_prompt_flag = self.update_forward_progress(eye_state)

        return {
            "timestamp_ms": int(time.time() * 1000),
            "blinck_call_flag": bool(blinck_call_flag),
            "stage_sound_prompt_flag": bool(stage_sound_prompt_flag),
            "blink_progress_ratio": float(progress_ratio),
            "debug_eye_bbox_xyxy": self.latest_eye_bbox,
            "debug_face_bbox_xyxy": self.latest_face_bbox,
            "debug_landmarks": self.latest_landmarks,
            "debug_info": "\n".join(
                [
                    f"eye_state: {eye_state}",
                    f"raw_eye_state: {raw_eye_state}",
                    f"confidence: {confidence:.3f}",
                    f"pattern_progress: {progress_ratio:.3f}",
                ]
            ),
        }

    def poll_latest_bbox(self):
        if self.pending_bbox_future is None or not self.pending_bbox_future.done():
            return

        try:
            result = self.pending_bbox_future.result()
        except Exception as exc:
            self.debug_info(f"[EyeRegionDetector] eye_region_error: {exc}")
            self.pending_bbox_future = None
            return

        self.latest_eye_bbox = [int(v) for v in result["eye_bbox_xyxy"]] if result["eye_bbox_xyxy"] else None
        self.latest_face_bbox = [int(v) for v in result["face_bbox_xyxy"]] if result["face_bbox_xyxy"] else None
        self.latest_landmarks = (
            [[int(point[0]), int(point[1])] for point in result["landmarks"]] if result["landmarks"] else None
        )
        if not self.latest_face_bbox:
            status = "no_face"
        elif not self.latest_landmarks:
            status = "landmarks_error"
        else:
            status = "ok" if self.latest_eye_bbox else "error"
        self.eye_region_status.emit(status)
        self.debug_info(f"[EyeRegionDetector] debug info: {result['debug_info']}", "eye_region")

        self.pending_bbox_future = None

    def submit_eye_region_detect_task(self, frame):
        if self.pending_bbox_future is not None:
            return

        if self.bbox_executor is None:
            self.bbox_executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="eye-region")

        self.pending_bbox_future = self.bbox_executor.submit(self.eye_region_detector.detect, frame.copy())

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
