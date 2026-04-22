from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget, QSizePolicy

from blink_call.modules.setting import SettingView


class HomeView(QWidget):
    def __init__(self, vm, nav):
        super().__init__()
        self.vm = vm
        self.nav = nav

        self.setObjectName("homeView")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.video_label = QLabel("未检测到可用摄像头，请在设置中配置")
        self.video_label.setObjectName("homeVideoLabel")
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        layout.addWidget(self.video_label)

        self.setting_btn = QPushButton("设置", self)
        self.setting_btn.setObjectName("homeSettingBtn")
        self.setting_btn.setFixedSize(88, 36)
        self.setting_btn.move(20, 20)
        self.setting_btn.clicked.connect(self.vm.open_settings)

        self.setting_popup = SettingView(self.vm.setting_vm, self)
        self.setting_popup.raise_()

        self.vm.frame_ready.connect(self._show_frame)
        self.vm.status_changed.connect(self._show_status)
        self.vm.show_settings_requested.connect(self._open_setting_popup)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.setting_popup.setGeometry(0, 0, self.width(), self.height())

    def _open_setting_popup(self):
        self.setting_popup.setGeometry(0, 0, self.width(), self.height())
        self.setting_popup.show()
        self.setting_popup.raise_()

    def _show_frame(self, image):
        pixmap = QPixmap.fromImage(image)
        self.video_label.setPixmap(
            pixmap.scaled(
                self.video_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self.video_label.setText("")

    def _show_status(self, text):
        self.video_label.setPixmap(QPixmap())
        self.video_label.setText(text)
