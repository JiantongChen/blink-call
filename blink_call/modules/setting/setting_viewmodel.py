from PySide6.QtCore import QObject, Signal


class SettingViewModel(QObject):
    close_requested = Signal()

    def __init__(self, model, on_apply, on_start_service):
        super().__init__()
        self.model = model
        self._on_apply = on_apply
        self._on_start_service = on_start_service

    def save_camera_config(self, mode, local_camera_id, remote_ip, remote_port):
        self.model.set_camera_config(mode, local_camera_id, remote_ip, remote_port)
        self._on_apply(mode, local_camera_id, remote_ip, remote_port)
        self.close_requested.emit()

    def start_local_service_only(self, local_camera_id):
        self._on_start_service(local_camera_id)
        self.close_requested.emit()
