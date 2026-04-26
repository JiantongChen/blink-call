import threading

import cv2
from flask import Flask, Response, jsonify
from werkzeug.serving import make_server

from blink_call.camera.local_capture import LocalCameraCapture


class LocalCameraFrameServer:
    def __init__(self, camera_id: int = 0, host: str = "0.0.0.0", port: int = 17925):
        self.camera_id = camera_id
        self.host = host
        self.port = port
        self.capture = LocalCameraCapture(camera_id=camera_id)

        self.app = Flask(__name__)
        self._http_server = None
        self._server_thread = None

        self._setup_routes()

    def _setup_routes(self):
        @self.app.route("/frame")
        def frame():
            if not self.capture.camera_found:
                return (
                    jsonify(
                        {
                            "message": "Camera does not exist.",
                            "camera_id": self.camera_id,
                        }
                    ),
                    599,
                )

            latest = self.capture.read_latest_frame()
            if latest is None:
                return jsonify({"message": "Frame is None."}), 598

            ok, buffer = cv2.imencode(".jpg", latest)
            if not ok:
                return jsonify({"message": "Encode failed."}), 597

            return Response(buffer.tobytes(), mimetype="image/jpeg")

    def start(self):
        started = self.capture.start()
        if not started:
            return False

        self._http_server = make_server(self.host, self.port, self.app)
        self._server_thread = threading.Thread(target=self._http_server.serve_forever, daemon=True)
        self._server_thread.start()
        return True

    def stop(self):
        if self._http_server is not None:
            self._http_server.shutdown()
            self._http_server.server_close()
            self._http_server = None

        self.capture.stop()
        self._server_thread = None

    def read_latest_frame(self):
        return self.capture.read_latest_frame()
