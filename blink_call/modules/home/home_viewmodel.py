import cv2
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

from blink_call.modules.setting import SettingModel, SettingViewModel


class HomeViewModel(QObject):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    show_settings_requested = Signal()
    language_changed = Signal(str)
    local_service_active_changed = Signal(bool)

    STATUS_TEXTS = {
        "zh": {
            "service_running": "\u6444\u50cf\u5934\u670d\u52a1\u5df2\u542f\u52a8\uff0c\u5f53\u524d\u9875\u9762\u4ec5\u663e\u793a\u670d\u52a1\u72b6\u6001\u3002",
            "remote_mode": "\u5f53\u524d\u4e3a\u8fdc\u7a0b\u6444\u50cf\u5934\u6a21\u5f0f\uff0c\u8bf7\u5728\u8bbe\u7f6e\u4e2d\u586b\u5199 IP \u548c Port\u3002",
            "no_camera": "\u672a\u68c0\u6d4b\u5230\u53ef\u7528\u6444\u50cf\u5934\uff0c\u8bf7\u5728\u8bbe\u7f6e\u4e2d\u914d\u7f6e\u3002",
            "service_started": "\u670d\u52a1\u5df2\u542f\u52a8\u3002\u8bf7\u5728\u5176\u4ed6\u8bbe\u5907\u9009\u62e9\u201c\u8fdc\u7a0b\u6444\u50cf\u5934\u201d\u3002\nIP: {ip}\nPort: {port}",
        },
        "en": {
            "service_running": "Camera service is running. This page shows service status only.",
            "remote_mode": "Remote camera mode is active. Set IP and port in Settings.",
            "no_camera": "No available camera detected. Please configure it in Settings.",
            "service_started": 'Service started. On another device choose "Remote Camera".\nIP: {ip}\nPort: {port}',
        },
    }

    def __init__(self, model):
        super().__init__()
        self.model = model

        (
            self.camera_mode,
            self.local_camera_id,
            self.remote_ip,
            self.remote_port,
        ) = self.model.load_camera_config()
        self.service_camera_id, self.service_port = self.model.load_local_service_config()
        self.ui_language = self.model.load_ui_language()

        self.setting_model = SettingModel()
        self.setting_model.set_language(self.ui_language)
        self.setting_model.set_camera_config(
            self.camera_mode,
            self.local_camera_id if self.local_camera_id is not None else 0,
            self.remote_ip,
            self.remote_port,
        )
        self.setting_model.set_service_config(self.service_camera_id, self.service_port)
        self.setting_vm = SettingViewModel(
            self.setting_model,
            self.apply_camera_config,
            self.save_local_service_config,
            self.start_local_camera_service,
            self.restore_default_config,
            self.change_language,
        )

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._update_frame)
        self._last_status_key = None
        self._last_status_params = {}

    def _t(self, key):
        return self.STATUS_TEXTS.get(self.ui_language, self.STATUS_TEXTS["zh"])[key]

    def _emit_status(self, key, **params):
        self._last_status_key = key
        self._last_status_params = params
        self.status_changed.emit(self._t(key).format(**params))

    def on_page_enter(self):
        self._start_home_camera()

    def _start_home_camera(self):
        if self.model.service_server is not None:
            self.timer.stop()
            self.local_service_active_changed.emit(True)
            self._emit_status("service_running")
            return

        if self.camera_mode != "local":
            self.timer.stop()
            self.local_service_active_changed.emit(False)
            self._emit_status("remote_mode")
            return

        ok = self.model.open_camera(self.local_camera_id)
        if not ok:
            self.timer.stop()
            self.local_service_active_changed.emit(False)
            self._emit_status("no_camera")
            return

        self.local_service_active_changed.emit(False)
        self.timer.start()

    def _update_frame(self):
        frame = self.model.read_frame()
        if frame is None:
            self.timer.stop()
            self.local_service_active_changed.emit(False)
            self._emit_status("no_camera")
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self.frame_ready.emit(image)

    def open_settings(self):
        self.show_settings_requested.emit()

    def apply_camera_config(self, mode, local_camera_id, remote_ip, remote_port):
        self.camera_mode = mode
        self.local_camera_id = local_camera_id if mode == "local" else None
        self.remote_ip = remote_ip
        self.remote_port = int(remote_port)

        self.setting_model.set_camera_config(
            mode,
            local_camera_id,
            remote_ip,
            self.remote_port,
        )
        self.model.save_camera_config(
            self.camera_mode,
            self.local_camera_id,
            self.remote_ip,
            self.remote_port,
        )
        self._start_home_camera()

    def save_local_service_config(self, camera_id, port):
        self.service_camera_id = int(camera_id)
        self.service_port = int(port)
        self.setting_model.set_service_config(self.service_camera_id, self.service_port)
        self.model.save_local_service_config(self.service_camera_id, self.service_port)

    def start_local_camera_service(self, local_camera_id, service_port):
        self.save_local_service_config(local_camera_id, service_port)
        ok, ip, port = self.model.start_local_camera_service(local_camera_id, service_port)
        self.timer.stop()

        if not ok:
            self.local_service_active_changed.emit(False)
            self._emit_status("no_camera")
            return

        self.local_service_active_changed.emit(True)
        self._emit_status("service_started", ip=ip, port=port)

    def restore_default_config(self):
        self.model.reset_camera_config_to_default()
        (
            self.camera_mode,
            self.local_camera_id,
            self.remote_ip,
            self.remote_port,
        ) = self.model.load_camera_config()
        self.service_camera_id, self.service_port = self.model.load_local_service_config()
        self.ui_language = self.model.load_ui_language()

        self.setting_model.set_language(self.ui_language)
        self.setting_model.set_camera_config(
            self.camera_mode,
            self.local_camera_id if self.local_camera_id is not None else 0,
            self.remote_ip,
            self.remote_port,
        )
        self.setting_model.set_service_config(self.service_camera_id, self.service_port)
        self._start_home_camera()

    def change_language(self, language):
        self.ui_language = language
        self.setting_model.set_language(language)
        self.model.save_ui_language(language)
        self.language_changed.emit(language)
        if not self.timer.isActive() and self._last_status_key:
            self._emit_status(self._last_status_key, **self._last_status_params)

    def exit_local_service_mode(self):
        self.model.stop_local_camera_service()
        self.local_service_active_changed.emit(False)
        self._start_home_camera()
