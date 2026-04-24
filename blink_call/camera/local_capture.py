import threading
import time

import cv2


class LocalCameraCapture:
    def __init__(self, camera_id: int = 0):
        self.camera_id = camera_id

        self.cap = None
        self.running = False
        self.camera_found = False
        self.latest_frame = None

        self._lock = threading.Lock()
        self._thread = None

    def start(self):
        if self.running:
            return True

        cap = cv2.VideoCapture(self.camera_id)
        if not cap.isOpened():
            cap.release()
            self.camera_found = False
            return False

        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release()
            self.camera_found = False
            return False

        self.cap = cap
        self.camera_found = True
        with self._lock:
            self.latest_frame = frame

        self.running = True
        self._thread = threading.Thread(target=self._capture_loop, daemon=True)
        self._thread.start()
        return True

    def _capture_loop(self):
        while self.running and self.cap is not None:
            ok, frame = self.cap.read()
            if ok and frame is not None:
                with self._lock:
                    self.latest_frame = frame
            else:
                self.camera_found = False
                time.sleep(0.05)

    def read_latest_frame(self):
        with self._lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def stop(self):
        self.running = False
        if self.cap is not None:
            self.cap.release()
            self.cap = None
