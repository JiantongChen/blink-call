import cv2
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

from blink_call.modules.home.home_model import HomeModel
from blink_call.modules.setting.setting_model import SettingModel
from blink_call.modules.setting.setting_viewmodel import SettingViewModel


class HomeViewModel(QObject):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    local_service_active_changed = Signal(bool)

    STATUS_TEXTS = {
        "zh": {
            "service_running": "摄像头服务已启动，当前页面仅显示服务状态。",
            "remote_mode": "当前为远程摄像头模式，请在设置中填写 IP 和 Port。",
            "no_camera": "未检测到可用摄像头，请在设置中配置。",
            "remote_camera_not_found": "远程摄像头不存在。",
            "cannot_connect": "无法连接远程摄像头服务。",
            "service_started": "服务已启动。请在其他设备选择“远程摄像头”。\nIP: {ip}\nPort: {port}",
        },
        "en": {
            "service_running": "Camera service is running. This page shows service status only.",
            "remote_mode": "Remote camera mode is active. Set IP and port in Settings.",
            "no_camera": "No available camera detected. Please configure it in Settings.",
            "remote_camera_not_found": "Remote camera not found.",
            "cannot_connect": "Unable to connect to remote camera service.",
            "service_started": 'Service started. On another device choose "Remote Camera".\nIP: {ip}\nPort: {port}',
        },
    }

    def __init__(self, model: HomeModel):
        super().__init__()
        self.model = model

        self.setting_model = SettingModel()
        self.setting_vm = SettingViewModel(self.setting_model)
        self.setting_vm.save_setting.connect(self.on_page_enter)
        self.setting_vm.start_local_service.connect(self.start_local_camera_service)

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._update_frame)

    def _t(self, key):
        return self.STATUS_TEXTS.get(self.setting_vm.get_config("ui.language"), self.STATUS_TEXTS["zh"])[key]

    def _emit_status(self, key, **params):
        self.status_changed.emit(self._t(key).format(**params))

    def on_page_enter(self):
        self._start_home_camera()

    def _start_home_camera(self):
        self.model.stop_local_camera_service()

        if self.setting_model.get_config("camera.mode") == "local":
            local_camera_id = self.setting_vm.get_config("camera.local_camera_id")
            ok = self.model.start_local_capture(local_camera_id)
            if not ok:
                self.timer.stop()
                self.local_service_active_changed.emit(False)
                self._emit_status("no_camera")
                return

            self.local_service_active_changed.emit(False)
            self.timer.start()
            return

        if self.setting_model.get_config("camera.mode") == "remote":
            remote_ip = self.setting_vm.get_config("camera.remote.ip")
            remote_port = self.setting_vm.get_config("camera.remote.port")
            ok = self.model.start_remote_capture(remote_ip, remote_port)
            if not ok:
                self.timer.stop()
                self.local_service_active_changed.emit(False)
                self._emit_status("cannot_connect")
                return

            self.local_service_active_changed.emit(False)
            self.timer.start()
            self._emit_status("remote_mode")
            return

        self.timer.stop()
        self.local_service_active_changed.emit(False)

    def _update_frame(self):
        frame = self.model.read_frame()
        if frame is None:
            status = self.model.get_status()
            if status == "remote_camera_not_found":
                self._emit_status("remote_camera_not_found")
            elif status == "cannot_connect":
                self._emit_status("cannot_connect")
            else:
                self._emit_status("no_camera")
            return

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self.frame_ready.emit(image)

    def start_local_camera_service(self):
        local_camera_id = self.setting_vm.get_config("local_service.camera_id", source="temp")
        service_port = self.setting_vm.get_config("local_service.port", source="temp")
        ok, ip, port = self.model.start_local_camera_service(local_camera_id, service_port)
        self.timer.stop()

        if not ok:
            self.local_service_active_changed.emit(False)
            self._emit_status("no_camera")
            return

        self.local_service_active_changed.emit(True)
        self._emit_status("service_started", ip=ip, port=port)

    def exit_local_service_mode(self):
        self.model.stop_local_camera_service()
        self.local_service_active_changed.emit(False)
        self._start_home_camera()
