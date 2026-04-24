import threading
import time
import urllib.error
import urllib.request

import cv2
import numpy as np


class RemoteCameraClient:
    STATUS_CONNECTING = "connecting"
    STATUS_OK = "ok"
    STATUS_CAMERA_NOT_FOUND = "remote_camera_not_found"
    STATUS_CANNOT_CONNECT = "cannot_connect"

    def __init__(self, ip: str, port: int, timeout: float = 3, interval: float = 0.2):
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.interval = interval

        self.running = False
        self.latest_frame = None
        self.status = self.STATUS_CONNECTING

        self._lock = threading.Lock()
        self._thread = None

    @property
    def frame_url(self):
        return f"http://{self.ip}:{self.port}/frame"

    def start(self):
        if self.running:
            return True

        self.running = True
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()
        return True

    def _poll_loop(self):
        while self.running:
            time.sleep(self.interval)

            try:
                with urllib.request.urlopen(self.frame_url, timeout=self.timeout) as resp:
                    content_type = (resp.headers.get("Content-Type") or "").lower()
                    payload = resp.read()

                if "image/jpeg" not in content_type:
                    self._set_status(self.STATUS_CAMERA_NOT_FOUND)
                    self._set_frame(None)
                    continue

                image_data = np.frombuffer(payload, dtype=np.uint8)
                frame = cv2.imdecode(image_data, cv2.IMREAD_COLOR)
                if frame is None:
                    self._set_status(self.STATUS_CAMERA_NOT_FOUND)
                    self._set_frame(None)
                else:
                    self._set_frame(frame)
                    self._set_status(self.STATUS_OK)
            except urllib.error.HTTPError as exc:
                if exc.code == 404:
                    self._set_status(self.STATUS_CAMERA_NOT_FOUND)
                    self._set_frame(None)
                else:
                    self._set_status(self.STATUS_CANNOT_CONNECT)
                    self._set_frame(None)
            except (urllib.error.URLError, TimeoutError, OSError):
                self._set_status(self.STATUS_CANNOT_CONNECT)
                self._set_frame(None)

    def _set_frame(self, frame):
        with self._lock:
            self.latest_frame = frame

    def _set_status(self, status):
        self.status = status

    def read_latest_frame(self):
        with self._lock:
            if self.latest_frame is None:
                return None
            return self.latest_frame.copy()

    def get_status(self):
        return self.status

    def stop(self):
        self.running = False
