from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingView(QWidget):
    popup_closed = Signal()
    TRANSLATIONS = {
        "zh": {
            "title": "\u8bbe\u7f6e",
            "general_title": "\u901a\u7528\u8bbe\u7f6e",
            "language": "\u8bed\u8a00",
            "camera_title": "\u6444\u50cf\u5934",
            "choose_label": "\u8bf7\u9009\u62e9\u6444\u50cf\u5934\u6765\u6e90\uff1a",
            "local_radio": "\u672c\u5730\u6444\u50cf\u5934",
            "remote_radio": "\u8fdc\u7a0b\u6444\u50cf\u5934",
            "save_btn": "\u4fdd\u5b58\u8bbe\u7f6e",
            "close_btn": "\u5173\u95ed",
            "other_title": "\u5176\u4ed6\u8bbe\u7f6e",
            "reset_btn": "\u6062\u590d\u9ed8\u8ba4\u8bbe\u7f6e",
            "start_service_btn": "\u5355\u72ec\u542f\u52a8\u672c\u5730\u6444\u50cf\u5934\u670d\u52a1",
            "service_section_title": "\u5355\u72ec\u542f\u52a8\u672c\u5730\u6444\u50cf\u5934\u670d\u52a1",
            "service_id": "\u670d\u52a1 ID",
            "service_port": "\u670d\u52a1 Port",
            "unsaved_title": "\u672a\u4fdd\u5b58\u7684\u8bbe\u7f6e",
            "unsaved_msg": "\u53d1\u73b0\u6709\u672a\u4fdd\u5b58\u7684\u8bbe\u7f6e\uff0c\u662f\u5426\u4fdd\u5b58\uff1f",
            "confirm_reset_title": "\u6062\u590d\u9ed8\u8ba4\u8bbe\u7f6e",
            "confirm_reset_msg": "\u786e\u5b9a\u8981\u6062\u590d\u9ed8\u8ba4\u8bbe\u7f6e\u5417\uff1f",
            "confirm_btn": "\u786e\u5b9a",
        },
        "en": {
            "title": "Settings",
            "general_title": "General",
            "language": "Language",
            "camera_title": "Camera",
            "choose_label": "Choose camera source:",
            "local_radio": "Local camera",
            "remote_radio": "Remote camera",
            "save_btn": "Save settings",
            "close_btn": "Close",
            "other_title": "Other settings",
            "reset_btn": "Restore defaults",
            "start_service_btn": "Start local camera service only",
            "service_section_title": "Start local camera service only",
            "service_id": "Service ID",
            "service_port": "Service Port",
            "unsaved_title": "Unsaved settings",
            "unsaved_msg": "There are unsaved changes. Save before closing?",
            "confirm_reset_title": "Restore defaults",
            "confirm_reset_msg": "Are you sure to restore default settings?",
            "confirm_btn": "Confirm",
        },
    }

    def __init__(self, vm, parent=None):
        super().__init__(parent)
        self.vm = vm
        self.setVisible(False)
        self.panel = None
        self.current_language = "zh"
        self._saved_camera_state = {}

        self.setObjectName("settingOverlay")

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(120, 60, 120, 60)

        self.panel = QFrame()
        self.panel.setObjectName("settingPanel")
        root_layout.addWidget(self.panel)

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(20, 20, 20, 20)
        panel_layout.setSpacing(16)

        self.title_label = QLabel("Settings")
        self.title_label.setObjectName("settingTitle")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        panel_layout.addWidget(self.title_label)

        general_group = QFrame()
        general_group.setObjectName("settingGeneralGroup")
        panel_layout.addWidget(general_group)

        general_layout = QVBoxLayout(general_group)
        general_layout.setContentsMargins(16, 16, 16, 16)
        general_layout.setSpacing(10)

        self.general_title_label = QLabel("General")
        self.general_title_label.setObjectName("settingSectionTitle")
        self.general_title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        general_layout.addWidget(self.general_title_label)

        general_divider = QFrame()
        general_divider.setObjectName("settingSectionDivider")
        general_divider.setFrameShape(QFrame.Shape.HLine)
        general_layout.addWidget(general_divider)

        language_row = QHBoxLayout()
        self.language_label = QLabel("Language")
        self.language_combo = QComboBox()
        self.language_combo.addItem("\u4e2d\u6587", "zh")
        self.language_combo.addItem("English", "en")
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language_combo)
        language_row.addStretch()
        general_layout.addLayout(language_row)

        camera_group = QFrame()
        camera_group.setObjectName("settingCameraGroup")
        panel_layout.addWidget(camera_group)

        camera_layout = QVBoxLayout(camera_group)
        camera_layout.setContentsMargins(16, 16, 16, 16)
        camera_layout.setSpacing(10)

        self.camera_title_label = QLabel("Camera")
        self.camera_title_label.setObjectName("settingSectionTitle")
        self.camera_title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        camera_layout.addWidget(self.camera_title_label)

        camera_divider = QFrame()
        camera_divider.setObjectName("settingSectionDivider")
        camera_divider.setFrameShape(QFrame.Shape.HLine)
        camera_layout.addWidget(camera_divider)

        self.choose_label = QLabel("Choose camera source:")
        self.choose_label.setObjectName("settingChooseLabel")
        camera_layout.addWidget(self.choose_label)

        self.local_radio = QRadioButton("Local camera")
        camera_layout.addWidget(self.local_radio)

        local_id_row = QHBoxLayout()
        local_id_row.addSpacing(24)
        self.local_id_label = QLabel("ID")
        self.local_id = QSpinBox()
        self.local_id.setMinimum(0)
        self.local_id.setMaximum(20)
        local_id_row.addWidget(self.local_id_label)
        local_id_row.addWidget(self.local_id)
        local_id_row.addStretch()
        camera_layout.addLayout(local_id_row)

        self.remote_radio = QRadioButton("Remote camera")
        camera_layout.addWidget(self.remote_radio)

        remote_row = QHBoxLayout()
        remote_row.addSpacing(24)
        self.remote_ip_label = QLabel("IP")
        self.remote_ip = QLineEdit()
        self.remote_ip.setPlaceholderText("IP")
        self.remote_port_label = QLabel("Port")
        self.remote_port = QSpinBox()
        self.remote_port.setMinimum(1)
        self.remote_port.setMaximum(65535)
        self.remote_ip.setFixedWidth(220)
        self.remote_port.setFixedWidth(220)
        remote_row.addWidget(self.remote_ip_label)
        remote_row.addWidget(self.remote_ip)
        remote_row.addWidget(self.remote_port_label)
        remote_row.addWidget(self.remote_port)
        remote_row.addStretch()
        camera_layout.addLayout(remote_row)

        radio_group = QButtonGroup(self)
        radio_group.addButton(self.local_radio)
        radio_group.addButton(self.remote_radio)

        other_group = QFrame()
        other_group.setObjectName("settingOtherGroup")
        panel_layout.addWidget(other_group)

        other_layout = QVBoxLayout(other_group)
        other_layout.setContentsMargins(16, 16, 16, 16)
        other_layout.setSpacing(10)

        self.other_title_label = QLabel("Other settings")
        self.other_title_label.setObjectName("settingSectionTitle")
        self.other_title_label.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        other_layout.addWidget(self.other_title_label)

        other_divider = QFrame()
        other_divider.setObjectName("settingSectionDivider")
        other_divider.setFrameShape(QFrame.Shape.HLine)
        other_layout.addWidget(other_divider)

        self.service_section_label = QLabel("Start local camera service only")
        self.service_section_label.setObjectName("settingSubSectionTitle")
        other_layout.addWidget(self.service_section_label)

        service_cfg_row = QHBoxLayout()
        service_cfg_row.addSpacing(24)
        self.service_id_label = QLabel("Service ID")
        self.service_camera_id = QSpinBox()
        self.service_camera_id.setMinimum(0)
        self.service_camera_id.setMaximum(20)
        self.service_camera_id.setFixedWidth(120)
        self.service_port_label = QLabel("Service Port")
        self.service_port = QSpinBox()
        self.service_port.setMinimum(1)
        self.service_port.setMaximum(65535)
        self.service_port.setFixedWidth(120)
        service_cfg_row.addWidget(self.service_id_label)
        service_cfg_row.addWidget(self.service_camera_id)
        service_cfg_row.addWidget(self.service_port_label)
        service_cfg_row.addWidget(self.service_port)
        service_cfg_row.addStretch()
        other_layout.addLayout(service_cfg_row)

        start_btn_row = QHBoxLayout()
        start_btn_row.addSpacing(24)
        self.start_service_btn = QPushButton("Start local camera service only")
        self.start_service_btn.setObjectName("settingStartServiceBtn")
        start_btn_row.addWidget(self.start_service_btn)
        start_btn_row.addStretch()
        other_layout.addLayout(start_btn_row)

        other_layout.addSpacing(14)

        reset_btn_row = QHBoxLayout()
        self.reset_btn = QPushButton("Restore defaults")
        self.reset_btn.setObjectName("settingResetBtn")
        reset_btn_row.addWidget(self.reset_btn)
        reset_btn_row.addStretch()
        other_layout.addLayout(reset_btn_row)

        panel_layout.addStretch()

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save settings")
        self.save_btn.setObjectName("settingSaveBtn")
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("settingCloseBtn")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.close_btn)
        panel_layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self._save)
        self.close_btn.clicked.connect(self._close_with_unsaved_check)
        self.reset_btn.clicked.connect(self._restore_default)
        self.start_service_btn.clicked.connect(self._start_service)
        self.language_combo.currentIndexChanged.connect(self._on_language_changed)
        self.vm.close_requested.connect(self.hide)

        self._load_from_setting_model()

    def refresh_from_model(self):
        self._load_from_setting_model()

    def _load_from_setting_model(self):
        cfg = self.vm.model
        self.current_language = cfg.language
        language_idx = self.language_combo.findData(cfg.language)
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(0 if language_idx < 0 else language_idx)
        self.language_combo.blockSignals(False)
        self.local_id.setValue(int(cfg.local_camera_id or 0))
        self.remote_ip.setText(cfg.remote_ip or "")
        self.remote_port.setValue(int(cfg.remote_port or 10000))
        self.service_camera_id.setValue(int(cfg.service_camera_id or 0))
        self.service_port.setValue(int(cfg.service_port or 10000))
        if cfg.camera_mode == "remote":
            self.remote_radio.setChecked(True)
        else:
            self.local_radio.setChecked(True)
        self._saved_camera_state = self._current_camera_state()
        self._apply_language(cfg.language)

    def _current_camera_state(self):
        return {
            "mode": "local" if self.local_radio.isChecked() else "remote",
            "local_camera_id": self.local_id.value(),
            "remote_ip": self.remote_ip.text().strip(),
            "remote_port": self.remote_port.value(),
            "service_camera_id": self.service_camera_id.value(),
            "service_port": self.service_port.value(),
        }

    def _has_unsaved_camera_changes(self):
        return self._current_camera_state() != self._saved_camera_state

    def _on_language_changed(self, _index):
        language = self.language_combo.currentData()
        if not language:
            return
        self.current_language = language
        self.vm.change_language(language)
        self._apply_language(language)

    def _i18n(self):
        return self.TRANSLATIONS.get(self.current_language, self.TRANSLATIONS["zh"])

    def _apply_language(self, language):
        self.current_language = language
        i18n = self._i18n()
        self.title_label.setText(i18n["title"])
        self.general_title_label.setText(i18n["general_title"])
        self.language_label.setText(i18n["language"])
        self.camera_title_label.setText(i18n["camera_title"])
        self.choose_label.setText(i18n["choose_label"])
        self.local_radio.setText(i18n["local_radio"])
        self.remote_radio.setText(i18n["remote_radio"])
        self.save_btn.setText(i18n["save_btn"])
        self.close_btn.setText(i18n["close_btn"])
        self.other_title_label.setText(i18n["other_title"])
        self.reset_btn.setText(i18n["reset_btn"])
        self.start_service_btn.setText(i18n["start_service_btn"])
        self.service_section_label.setText(i18n["service_section_title"])
        self.service_id_label.setText(i18n["service_id"])
        self.service_port_label.setText(i18n["service_port"])

    def _save(self):
        mode = "local" if self.local_radio.isChecked() else "remote"
        self._saved_camera_state = self._current_camera_state()
        self.vm.save_camera_config(
            mode,
            self.local_id.value(),
            self.remote_ip.text().strip(),
            self.remote_port.value(),
            self.service_camera_id.value(),
            self.service_port.value(),
        )

    def _close_with_unsaved_check(self):
        if not self._has_unsaved_camera_changes():
            self.hide()
            return

        i18n = self._i18n()
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle(i18n["unsaved_title"])
        msg.setText(i18n["unsaved_msg"])
        save_btn = msg.addButton(i18n["save_btn"], QMessageBox.ButtonRole.AcceptRole)
        close_btn = msg.addButton(i18n["close_btn"], QMessageBox.ButtonRole.DestructiveRole)
        msg.exec()

        if msg.clickedButton() == save_btn:
            self._save()
        elif msg.clickedButton() == close_btn:
            self.hide()

    def _start_service(self):
        self.vm.start_local_service_only(
            self.service_camera_id.value(),
            self.service_port.value(),
        )

    def _restore_default(self):
        i18n = self._i18n()
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(i18n["confirm_reset_title"])
        msg.setText(i18n["confirm_reset_msg"])
        confirm_btn = msg.addButton(i18n["confirm_btn"], QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(i18n["close_btn"], QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == confirm_btn:
            self.vm.restore_default_config()
            self._load_from_setting_model()

    def showEvent(self, event):
        self._load_from_setting_model()
        super().showEvent(event)

    def hideEvent(self, event):
        self.popup_closed.emit()
        super().hideEvent(event)
