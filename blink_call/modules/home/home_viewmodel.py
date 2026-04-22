import cv2
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

from blink_call.modules.setting import SettingModel, SettingViewModel


class HomeViewModel(QObject):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    show_settings_requested = Signal()

    def __init__(self, model):
        super().__init__()
        self.model = model
        self.camera_mode = "local"
        self.local_camera_id = None
        self.remote_ip = ""
        self.remote_port = 10000

        self.setting_model = SettingModel()
        self.setting_vm = SettingViewModel(
            self.setting_model,
            self.apply_camera_config,
            self.start_local_camera_service,
        )

        self.timer = QTimer(self)
        self.timer.setInterval(33)
        self.timer.timeout.connect(self._update_frame)

    def on_page_enter(self):
        self._start_home_camera()

    def _start_home_camera(self):
        if self.model.service_server is not None:
            self.timer.stop()
            self.status_changed.emit("摄像头服务已启动，当前页面仅显示服务状态")
            return

        if self.camera_mode != "local":
            self.timer.stop()
            self.status_changed.emit("当前为指定其他摄像头模式，请在设置中填写 IP 和 Port")
            return

        ok = self.model.open_camera(self.local_camera_id)
        if not ok:
            self.timer.stop()
            self.status_changed.emit("未检测到可用摄像头，请在设置中配置")
            return

        self.timer.start()

    def _update_frame(self):
        frame = self.model.read_frame()
        if frame is None:
            self.timer.stop()
            self.status_changed.emit("未检测到可用摄像头，请在设置中配置")
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
        self.remote_port = remote_port
        self._start_home_camera()

    def start_local_camera_service(self, local_camera_id):
        ok, ip, port = self.model.start_local_camera_service(local_camera_id)
        self.timer.stop()

        if not ok:
            self.status_changed.emit("未检测到可用摄像头，请在设置中配置")
            return

        self.status_changed.emit(f'已启动摄像头服务，请在其他电脑选择"指定其他摄像头"，并填写ip和port为{ip}和{port}')
