import threading
from typing import Optional

from blink_call.camer_server.start_server import BlinkCameraServer
from blink_call.utils.helper import Helper


class HomeModel:
    def __init__(self):
        self.capture = None
        self.camera_id = None
        self.service_server = None
        self.service_thread = None

    def load_camera_config(self):
        default_camera_cfg = (Helper.get_default_config().get("camera") or {})
        default_remote_cfg = default_camera_cfg.get("remote") or {}

        local_config = Helper.get_local_config()
        camera_cfg = local_config.get("camera") or {}
        remote_cfg = camera_cfg.get("remote") or {}

        mode = camera_cfg.get("mode", default_camera_cfg.get("mode", "local"))
        local_camera_id = camera_cfg.get(
            "local_camera_id",
            default_camera_cfg.get("local_camera_id"),
        )
        remote_ip = remote_cfg.get("ip", default_remote_cfg.get("ip", ""))
        remote_port = remote_cfg.get(
            "port",
            default_remote_cfg.get("port", 10000),
        )
        try:
            remote_port = int(remote_port)
        except (TypeError, ValueError):
            remote_port = int(default_remote_cfg.get("port", 10000))

        return mode, local_camera_id, remote_ip, remote_port

    def save_camera_config(self, mode, local_camera_id, remote_ip, remote_port):
        Helper.update_local_config(
            {
                "camera": {
                    "mode": mode,
                    "local_camera_id": local_camera_id if mode == "local" else None,
                    "remote": {
                        "ip": remote_ip,
                        "port": int(remote_port),
                    },
                }
            }
        )

    def reset_camera_config_to_default(self):
        Helper.reset_local_config_to_default()
        return self.load_camera_config()

    def open_camera(self, camera_id: Optional[int]):
        self.release_camera()

        cap, camera_id = BlinkCameraServer.open_camera(camera_index=camera_id)
        if cap is None:
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
            return True, BlinkCameraServer.get_local_ip(), self.service_server.port

        self.release_camera()

        server = BlinkCameraServer(camera_index=camera_id)
        if not server.camera_available():
            return False, None, None

        thread = threading.Thread(target=server.run, daemon=True)
        thread.start()

        self.service_server = server
        self.service_thread = thread

        return True, BlinkCameraServer.get_local_ip(), server.port
