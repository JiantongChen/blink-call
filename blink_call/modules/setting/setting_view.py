from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingView(QWidget):
    def __init__(self, vm, parent=None):
        super().__init__(parent)
        self.vm = vm
        self.setVisible(False)

        self.setObjectName("settingOverlay")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(120, 60, 120, 60)

        panel = QFrame()
        panel.setObjectName("settingPanel")
        root_layout.addWidget(panel)

        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(16)

        title = QLabel("Settings")
        title.setObjectName("settingTitle")
        panel_layout.addWidget(title)

        camera_group = QFrame()
        camera_group.setObjectName("settingCameraGroup")
        panel_layout.addWidget(camera_group)

        camera_layout = QVBoxLayout(camera_group)
        camera_layout.setContentsMargins(16, 16, 16, 16)
        camera_layout.setSpacing(12)

        section_title = QLabel("Camera")
        section_title.setObjectName("settingSectionTitle")
        camera_layout.addWidget(section_title)

        choose_label = QLabel("Choose camera source:")
        choose_label.setObjectName("settingChooseLabel")
        camera_layout.addWidget(choose_label)

        local_row = QHBoxLayout()
        self.local_radio = QRadioButton("Local camera")
        self.local_id = QSpinBox()
        self.local_id.setMinimum(0)
        self.local_id.setMaximum(20)
        local_row.addWidget(self.local_radio)
        local_row.addWidget(QLabel("ID"))
        local_row.addWidget(self.local_id)
        local_row.addStretch()
        camera_layout.addLayout(local_row)

        remote_row = QGridLayout()
        self.remote_radio = QRadioButton("Remote camera")
        self.remote_ip = QLineEdit()
        self.remote_ip.setPlaceholderText("IP")
        self.remote_port = QSpinBox()
        self.remote_port.setMinimum(1)
        self.remote_port.setMaximum(65535)

        remote_row.addWidget(self.remote_radio, 0, 0, 1, 2)
        remote_row.addWidget(QLabel("IP"), 1, 0)
        remote_row.addWidget(self.remote_ip, 1, 1)
        remote_row.addWidget(QLabel("Port"), 2, 0)
        remote_row.addWidget(self.remote_port, 2, 1)
        camera_layout.addLayout(remote_row)

        radio_group = QButtonGroup(self)
        radio_group.addButton(self.local_radio)
        radio_group.addButton(self.remote_radio)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save settings")
        self.save_btn.setObjectName("settingSaveBtn")
        self.reset_btn = QPushButton("Restore defaults")
        self.reset_btn.setObjectName("settingResetBtn")
        self.start_service_btn = QPushButton("Start local camera service only")
        self.start_service_btn.setObjectName("settingStartServiceBtn")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.reset_btn)
        btn_row.addWidget(self.start_service_btn)
        panel_layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self._save)
        self.reset_btn.clicked.connect(self._restore_default)
        self.start_service_btn.clicked.connect(self._start_service)
        self.vm.close_requested.connect(self.hide)

        self._load_from_setting_model()

    def _load_from_setting_model(self):
        cfg = self.vm.model
        self.local_id.setValue(int(cfg.local_camera_id or 0))
        self.remote_ip.setText(cfg.remote_ip or "")
        self.remote_port.setValue(int(cfg.remote_port or 10000))
        if cfg.camera_mode == "remote":
            self.remote_radio.setChecked(True)
        else:
            self.local_radio.setChecked(True)

    def _save(self):
        mode = "local" if self.local_radio.isChecked() else "remote"
        self.vm.save_camera_config(
            mode,
            self.local_id.value(),
            self.remote_ip.text().strip(),
            self.remote_port.value(),
        )

    def _start_service(self):
        self.vm.start_local_service_only(self.local_id.value())

    def _restore_default(self):
        self.vm.restore_default_config()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.hide()
        super().mousePressEvent(event)
