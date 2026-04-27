import cv2
from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QImage

from blink_call.core.inference_worker import InferenceWorker
from blink_call.modules.home.home_model import HomeModel
from blink_call.modules.setting.setting_model import SettingModel
from blink_call.modules.setting.setting_viewmodel import SettingViewModel
from blink_call.utils.debug_overlay import draw_debug


class HomeViewModel(QObject):
    frame_ready = Signal(QImage)
    status_changed = Signal(str)
    local_service_active_changed = Signal(bool)
    debug_message = Signal(str)
    debug_mode_changed = Signal(bool)
    debug_cleared = Signal()

    STATUS_TEXTS = {
        "zh": {
            "local_invalid_camera": "摄像头不可用。\n如果确定此电脑存在可用摄像头，请在设置中配置。",
            "remote_error": "远程连接摄像头不可用(状态码: {status_code})。",
            "unknown_error": "发生未知错误。",
            "service_started_faild": "本地摄像头服务启动失败，请确认摄像头可用。",
            "service_started_success": "服务已启动，请在其他设备选择“远程摄像头”。\n地址: {ip}\n端口: {port}",
        },
        "en": {
            "local_invalid_camera": "Camera is not available.\nIf a camera exists on this device, please configure it in Settings.",
            "remote_error": "Remote camera is unavailable (status code: {status_code}).",
            "unknown_error": "An unknown error occurred.",
            "service_started_faild": "Failed to start local camera service. Please make sure the camera is available.",
            "service_started_success": 'Service started. On another device, choose "Remote Camera".\nIP: {ip}\nPort: {port}',
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
        self.timer.timeout.connect(self.update_frame)

        self.infer_worker = InferenceWorker(self.model)
        self.infer_worker.result_ready.connect(self.on_infer_result)
        self.infer_worker.debug_message.connect(self.on_infer_debug)
        self._debug_mode = bool(self.setting_vm.get_config("debug_mode"))
        self._latest_infer_result = None

    def emit_status(self, key, **params):
        _t = self.STATUS_TEXTS.get(self.setting_vm.get_config("ui.language"), self.STATUS_TEXTS["zh"])[key]
        self.status_changed.emit(_t.format(**params))

    def on_page_enter(self):
        self.sync_debug_mode()
        self.start_local_camera()

    def start_local_camera(self):
        self.local_service_active_changed.emit(False)

        if self.setting_model.get_config("camera.mode") == "remote":
            remote_ip = self.setting_vm.get_config("camera.remote.ip")
            remote_port = self.setting_vm.get_config("camera.remote.port")
            self.model.start_remote_capture(remote_ip, remote_port)
            self.timer.start()
            self.start_infer_worker()

        else:
            local_camera_id = self.setting_vm.get_config("camera.local_camera_id")
            ok = self.model.start_local_capture(local_camera_id)

            self.timer.start() if ok else self.timer.stop()
            self.start_infer_worker() if ok else self.stop_infer_worker()
            if not ok:
                self.emit_status("local_invalid_camera")

    def update_frame(self):
        _mode, frame, status_code = self.model.read_frame()
        if frame is None:
            if _mode == "local":
                self.emit_status("local_invalid_camera")
            elif _mode == "remote":
                self.emit_status("remote_error", status_code=status_code)
            else:
                self.emit_status("unknown_error")
            return

        if self._debug_mode and isinstance(self._latest_infer_result, dict):
            frame = draw_debug(frame, self._latest_infer_result)

        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb.shape
        image = QImage(rgb.data, w, h, ch * w, QImage.Format.Format_RGB888).copy()
        self.frame_ready.emit(image)

    def start_local_camera_service(self):
        local_camera_id = self.setting_vm.get_config("local_service.camera_id", source="temp")
        service_port = self.setting_vm.get_config("local_service.port", source="temp")
        ok, ip, port = self.model.start_local_camera_service(local_camera_id, service_port)

        self.timer.stop()
        self.stop_infer_worker()
        self.local_service_active_changed.emit(True)

        if ok:
            self.emit_status("service_started_success", ip=ip, port=port)
        else:
            self.emit_status("service_started_faild")

    def on_infer_result(self, result):
        self._latest_infer_result = result

    def on_infer_debug(self, text: str):
        if self._debug_mode:
            self.debug_message.emit(text)

    def sync_debug_mode(self):
        new_mode = bool(self.setting_vm.get_config("debug_mode"))
        if new_mode and not self._debug_mode:
            self.debug_cleared.emit()
        self._debug_mode = new_mode
        self.debug_mode_changed.emit(new_mode)

    def start_infer_worker(self):
        if not self.infer_worker.isRunning():
            self.infer_worker.start()

    def stop_infer_worker(self):
        self.infer_worker.stop()
        if self.infer_worker.isRunning():
            self.infer_worker.wait()

    def stop_all(self):
        self.timer.stop()
        self.stop_infer_worker()
        self.model.stop()
