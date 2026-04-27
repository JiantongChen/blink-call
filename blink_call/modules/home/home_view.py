from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from blink_call.core.navigation import Navigation
from blink_call.modules.home.home_viewmodel import HomeViewModel
from blink_call.modules.setting.setting_view import SettingView


class HomeView(QWidget):
    TEXTS = {
        "zh": {
            "settings": "设置",
            "exit": "退出",
        },
        "en": {
            "settings": "Settings",
            "exit": "Exit",
        },
    }

    def __init__(self, vm: HomeViewModel, nav: Navigation):
        super().__init__()
        self.vm = vm
        self.nav = nav

        self.setObjectName("homeView")

        i18n = self.TEXTS.get(self.vm.setting_vm.get_config("ui.language"), self.TEXTS["zh"])

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel()
        self.video_label.setObjectName("homeVideoLabel")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Ignored)
        layout.addWidget(self.video_label)

        self.setting_btn = QPushButton(i18n["settings"], self)
        self.setting_btn.setObjectName("homeSettingBtn")
        self.setting_btn.setFixedSize(88, 36)
        self.setting_btn.move(20, 20)
        self.setting_btn.clicked.connect(self.on_open_setting_popup)

        self.setting_popup = SettingView(self.vm.setting_vm, self)
        self.setting_popup.raise_()
        self.setting_popup.setVisible(False)
        self.setting_popup.close_setting_popup.connect(self.on_close_setting_popup)

        self.exit_btn = QPushButton(i18n["exit"], self)
        self.exit_btn.setObjectName("homeExitBtn")
        self.exit_btn.setFixedSize(156, 48)
        self.exit_btn.setVisible(False)
        self.exit_btn.clicked.connect(self.vm.on_page_enter)

        self.debug_info = QPlainTextEdit(self)
        self.debug_info.setObjectName("homeDebugInfo")
        self.debug_info.setReadOnly(True)
        self.debug_info.setVisible(False)
        self.debug_info.setMaximumBlockCount(100)

        self.vm.frame_ready.connect(self.on_show_frame)
        self.vm.show_camera_status.connect(self.on_show_camera_status)
        self.vm.debug_mode_state.connect(self.on_set_debug_visible)
        self.vm.show_debug_msg.connect(self.on_show_debug_msg)
        self.vm.clear_debug_msg.connect(self.on_clear_debug_msg)
        self.vm.setting_vm.language_changed.connect(self.on_apply_language)
        self.vm.local_service_status.connect(self.on_set_service_mode)

    def on_apply_language(self, language):
        i18n = self.TEXTS.get(language, self.TEXTS["zh"])
        self.setting_btn.setText(i18n["settings"])
        self.exit_btn.setText(i18n["exit"])

    def on_open_setting_popup(self):
        self.setting_btn.setVisible(False)
        self.setting_popup.refresh_from_model()
        self.setting_popup.setGeometry(0, 0, self.width(), self.height())
        self.setting_popup.show()
        self.setting_popup.raise_()

    def on_close_setting_popup(self):
        self.setting_btn.setVisible(True)

    def on_show_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.video_label.setText("")

    def on_show_camera_status(self, text):
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText(text)

    def on_set_service_mode(self, active: bool):
        self.setting_btn.setVisible(not active)
        self.exit_btn.setVisible(active)
        if active:
            self.debug_info.setVisible(False)

    def on_set_debug_visible(self, visible: bool):
        self.debug_info.setVisible(visible)

    def on_clear_debug_msg(self):
        self.debug_info.clear()

    def on_show_debug_msg(self, text: str):
        self.debug_info.appendPlainText(text)

        if not self.vm.setting_vm.get_config("debug_log.save_to_local"):
            return

        log_dir = self.vm.setting_vm.get_config("debug_log.local_dir") or str(Path.home() / "Desktop")
        log_path = Path(log_dir) / "blink_call.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)

        lines = text.splitlines() or [text]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        try:
            with log_path.open("a", encoding="utf-8") as f:
                for line in lines:
                    f.write(f"[{timestamp}] {line}\n")
        except OSError:
            return

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setting_popup.setGeometry(0, 0, self.width(), self.height())
        self._position_exit_btn()
        self._position_debug_info()

    def _position_exit_btn(self):
        x = (self.width() - self.exit_btn.width()) // 2
        y = int(self.height() * 0.78)
        self.exit_btn.move(max(0, x), max(0, y))

    def _position_debug_info(self):
        panel_width = min(max(int(self.width() * 0.3), 300), 400)
        panel_height = max(int(self.height() * 0.5), 300)
        x = self.width() - panel_width - 20
        y = 20
        self.debug_info.setGeometry(max(0, x), max(0, y), panel_width, panel_height)
