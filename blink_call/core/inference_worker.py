import time

import numpy as np
from PySide6.QtCore import QThread, Signal


class InferenceWorker(QThread):
    result_ready = Signal(dict)
    debug_message = Signal(str)

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.running = True
        self.count = 1
        self.min_interval = 1.0 / 10.0
        self.last_time = 0

    def run(self):
        self.running = True
        while self.running:
            frame = self.model.read_frame()[1]

            if frame is None:
                self.debug_message.emit("frame is None")
                continue

            now = time.perf_counter()
            if now - self.last_time < self.min_interval:
                continue
            self.last_time = now

            result = self.infer(frame)

            self.result_ready.emit(result)

    def infer(self, frame):
        self.debug_message.emit(f"infer#{self.count} frame_shape={np.shape(frame)}")
        self.count += 1

        return {"blink": False, "score": 0.0}

    def stop(self):
        self.running = False
