import argparse
import socket

import cv2
from flask import Flask, Response, jsonify

from blink_call.utils.helper import Helper


class BlinkCameraServer:
    def __init__(self, camera_index=None, max_index=10, host="0.0.0.0", port=None):
        self.camera_index = camera_index
        self.max_index = max_index
        self.host = host

        self.app = Flask(__name__)
        self.cap = self._open_camera()
        self.port = port or Helper.get_available_port()

        self._setup_routes()

    @staticmethod
    def find_camera_index(max_index=10):
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

    @staticmethod
    def open_camera(camera_index=None, max_index=10):
        index = camera_index
        if index is None:
            index = BlinkCameraServer.find_camera_index(max_index=max_index)
            if index is None:
                return None, None

        cap = cv2.VideoCapture(index)
        if not cap.isOpened():
            cap.release()
            return None, None

        ok, _ = cap.read()
        if not ok:
            cap.release()
            return None, None

        return cap, index

    def _open_camera(self):
        cap, index = self.open_camera(
            camera_index=self.camera_index,
            max_index=self.max_index,
        )
        if cap is None:
            return None

        self.camera_index = index
        return cap

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

    def camera_available(self):
        return self.cap is not None and self.cap.isOpened()

    def generate_frames(self):
        while self.camera_available():
            success, frame = self.cap.read()
            if not success:
                break

            _, buffer = cv2.imencode(".jpg", frame)
            frame_bytes = buffer.tobytes()

            yield (b"--frame\r\n" b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n\r\n")

    def _setup_routes(self):
        @self.app.route("/video")
        def video():
            return Response(
                self.generate_frames(),
                mimetype="multipart/x-mixed-replace; boundary=frame",
            )

        @self.app.route("/health")
        def health():
            camera_ok = self.camera_available()

            return jsonify(
                {
                    "status": "ok" if camera_ok else "error",
                    "camera": camera_ok,
                    "camera_index": self.camera_index,
                    "port": self.port,
                }
            )

    def run(self):
        if not self.camera_available():
            raise RuntimeError("No camera found")

        self.app.run(host=self.host, port=self.port, threaded=True)


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--camera-id", type=int, default=None)
    parser.add_argument("--port", type=int, default=None)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    server = BlinkCameraServer(
        camera_index=args.camera_id,
        host=args.host,
        port=args.port,
    )
    server.run()
