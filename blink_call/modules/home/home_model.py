import socket
import threading
from typing import Optional

import cv2

from blink_call.camer_server.start_server import BlinkCameraServer


class HomeModel:
    def __init__(self):
        self.capture = None
        self.camera_id = None
        self.service_server = None
        self.service_thread = None

    def find_camera_index(self, max_index=10):
        for idx in range(max_index):
            cap = cv2.VideoCapture(idx)
            if not cap.isOpened():
                cap.release()
                continue

            ok, _ = cap.read()
            cap.release()
            if ok:
                return idx

        return None

    def open_camera(self, camera_id: Optional[int]):
        self.release_camera()

        if camera_id is None:
            camera_id = self.find_camera_index()
            if camera_id is None:
                return False

        cap = cv2.VideoCapture(camera_id)
        if not cap.isOpened():
            cap.release()
            return False

        ok, _ = cap.read()
        if not ok:
            cap.release()
            return False

        self.capture = cap
        self.camera_id = camera_id
        return True

    def read_frame(self):
        if self.capture is None:
            return None

        ok, frame = self.capture.read()
        if not ok:
            return None

        return frame

    def release_camera(self):
        if self.capture is not None:
            self.capture.release()
            self.capture = None

    def start_local_camera_service(self, camera_id: Optional[int]):
        if self.service_server is not None:
            return True, self.get_local_ip(), self.service_server.port

        self.release_camera()

        server = BlinkCameraServer(camera_index=camera_id)
        if not server.camera_available():
            return False, None, None

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        self.service_server = server
        self.service_thread = thread

        return True, self.get_local_ip(), server.port

    @staticmethod
    def get_local_ip():
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            sock.close()
