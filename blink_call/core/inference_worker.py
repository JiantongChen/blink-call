import time

import numpy as np
from PySide6.QtCore import QThread, Signal


class InferenceWorker(QThread):
    result_ready = Signal(dict)
    debug_message = Signal(str)

    def __init__(self, home_model):
        super().__init__()
        self.home_model = home_model

        self.running = True
        self.min_interval = 1.0 / 10.0
        self.last_time = 0

        self.count = 0

    def debug_info(self, text):
        self.debug_message.emit(text)

    def run(self):
        self.running = True
        while self.running:
            now = time.perf_counter()
            if now - self.last_time < self.min_interval:
                continue
            self.last_time = now

            frame = self.home_model.read_frame()[1]
            if frame is None:
                self.debug_info("frame is None")
                continue

            result = self.inference(frame)
            self.result_ready.emit(result)

    def inference(self, frame):
        self.count += 1
        self.debug_info(f"infer#{self.count} frame_shape={np.shape(frame)}")

        return {
            "blink": False,
            "score": 0.0,
            "debug_bbox_xyxy": [[55, 55, 200, 200], [100, 100, 150, 150]],
            "debug_info": "info_text_1\nlong_info_text_2",
        }

    def stop(self):
        self.running = False
