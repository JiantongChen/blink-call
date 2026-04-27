import time

import numpy as np
from PySide6.QtCore import QThread, Signal


class InferenceWorker(QThread):
    result_ready = Signal(dict)
    debug_message = Signal(str)

    def __init__(self, home_model):
        super().__init__()
        self.home_model = home_model
        self._initialize_vars()

    def _initialize_vars(self):
        self.running = True
        self.min_interval = 1.0 / 10.0
        self.last_time = 0

        self.stat_fps_interval = 10.0
        self.infer_fps_window_start = time.perf_counter()
        self.infer_fps_counter = 0

        self.count = 0

    def debug_info(self, text):
        self.debug_message.emit(text)

    def stat_fps(self):
        self.infer_fps_counter += 1

        now = time.perf_counter()
        elapsed = now - self.infer_fps_window_start

        if elapsed >= self.stat_fps_interval:
            infer_fps = self.infer_fps_counter / elapsed
            self.debug_info(f"inference_fps={infer_fps:.2f}")

            self.infer_fps_window_start = now
            self.infer_fps_counter = 0

    def stop(self):
        self.running = False

    def run(self):
        self._initialize_vars()
        while self.running:
            now = time.perf_counter()
            if now - self.last_time < self.min_interval:
                time.sleep(self.min_interval / 10.0)
                continue
            self.last_time = now

            frame = self.home_model.read_frame()[1]
            if frame is None:
                self.debug_info("frame is None")
                continue

            result = self.inference(frame)
            self.result_ready.emit(result)
            self.stat_fps()

    def inference(self, frame):
        self.count += 1
        if self.count % 10 == 0:
            self.debug_info(f"infer#{self.count} frame_shape={np.shape(frame)}")

        return {
            "blink": False,
            "debug_bbox_xyxy": [[55, 55, 200, 200], [100, 100, 150, 150]],
            "debug_info": "info_text_1\nlong_info_text_2",
        }
