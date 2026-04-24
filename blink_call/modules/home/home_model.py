from enum import Enum
from typing import Optional

from blink_call.camera.client import RemoteCameraClient
from blink_call.camera.local_capture import LocalCameraCapture
from blink_call.camera.server import LocalCameraFrameServer
from blink_call.utils.helper import Helper


class Mode(Enum):
    NONE = "none"
    LOCAL = "local"
    REMOTE = "remote"
    SERVER = "server"


class HomeModel:
    def __init__(self):
        self.local_capture: Optional[LocalCameraCapture] = None
        self.remote_client: Optional[RemoteCameraClient] = None
        self.service_server: Optional[LocalCameraFrameServer] = None

        self.active_mode = Mode.NONE

    def _stop_active_sources(self):
        if self.local_capture is not None:
            self.local_capture.stop()
            self.local_capture = None

        if self.remote_client is not None:
            self.remote_client.stop()
            self.remote_client = None

        if self.service_server is not None:
            self.service_server.stop()
            self.service_server = None

        self.active_mode = Mode.NONE

    def start_local_capture(self, camera_id: int):
        self._stop_active_sources()

        self.local_capture = LocalCameraCapture(camera_id)
        ok = self.local_capture.start()
        if not ok:
            return False

        self.active_mode = Mode.LOCAL
        return True

    def start_remote_capture(self, remote_ip: str, remote_port: int):
        self._stop_active_sources()

        self.remote_client = RemoteCameraClient(remote_ip, int(remote_port))
        self.remote_client.start()
        self.active_mode = Mode.REMOTE

    def start_local_camera_service(self, camera_id: int, port: int):
        self._stop_active_sources()

        service_port = Helper.get_available_port(port)
        self.service_server = LocalCameraFrameServer(
            camera_id=camera_id,
            port=service_port,
        )
        ok = self.service_server.start()
        if not ok:
            return False, None, None

        self.active_mode = Mode.SERVER
        return True, Helper.get_local_ip(), service_port

    def read_frame(self):
        if self.active_mode == Mode.LOCAL and self.local_capture is not None:
            frame = self.local_capture.read_latest_frame()
            return "local", frame, None

        if self.active_mode == Mode.REMOTE and self.remote_client is not None:
            status_code = self.remote_client.get_status_code()
            frame = self.remote_client.read_latest_frame()
            return "remote", frame, status_code

        return "unknown", None, None
