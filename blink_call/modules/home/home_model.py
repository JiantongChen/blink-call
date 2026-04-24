from enum import Enum
from typing import Optional

from blink_call.camera.client import RemoteCameraClient
from blink_call.camera.local_capture import LocalCameraCapture
from blink_call.camera.server import LocalCameraFrameServer
from blink_call.utils.helper import Helper


class Status(Enum):
    OK = "ok"
    NO_CAMERA = "no_camera"
    REMOTE_CAMERA_NOT_FOUND = "remote_camera_not_found"
    CANNOT_CONNECT = "cannot_connect"


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
        self._status = Status.OK

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

        capture = LocalCameraCapture(camera_id)
        ok = capture.start()
        if not ok:
            self._status = Status.NO_CAMERA
            return False

        self.local_capture = capture
        self.active_mode = Mode.LOCAL
        self._status = Status.OK
        return True

    def start_remote_capture(self, remote_ip: str, remote_port: int):
        self._stop_active_sources()

        client = RemoteCameraClient(remote_ip, int(remote_port))
        client.start()

        self.remote_client = client
        self.active_mode = Mode.REMOTE
        self._status = Status.OK
        return True

    def start_local_camera_service(self, camera_id: int, port: int):
        self._stop_active_sources()

        service_port = Helper.get_available_port(port)
        server = LocalCameraFrameServer(
            camera_id=camera_id,
            port=service_port,
        )
        ok = server.start()
        if not ok:
            self._status = Status.NO_CAMERA
            return False, None, None

        self.service_server = server
        self.active_mode = Mode.SERVER
        self._status = Status.OK
        return True, Helper.get_local_ip(), service_port

    def stop_local_camera_service(self):
        if self.service_server is not None:
            self.service_server.stop()
            self.service_server = None

        if self.active_mode == Mode.SERVER:
            self.active_mode = Mode.NONE

    def read_frame(self):
        if self.active_mode == Mode.LOCAL and self.local_capture is not None:
            frame = self.local_capture.read_latest_frame()
            if frame is None:
                self._status = Status.NO_CAMERA
                return None

            self._status = Status.OK
            return frame

        if self.active_mode == Mode.REMOTE and self.remote_client is not None:
            status = self.remote_client.get_status()
            frame = self.remote_client.read_latest_frame()
            if frame is None:
                if status == RemoteCameraClient.STATUS_CAMERA_NOT_FOUND:
                    self._status = Status.REMOTE_CAMERA_NOT_FOUND
                elif status in (
                    RemoteCameraClient.Status.CANNOT_CONNECT,
                    RemoteCameraClient.STATUS_CONNECTING,
                ):
                    self._status = Status.CANNOT_CONNECT
                else:
                    self._status = Status.CANNOT_CONNECT
                return None

            self._status = Status.OK
            return frame

        return None

    def get_status(self):
        return self._status
