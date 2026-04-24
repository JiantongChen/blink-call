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
    QScrollArea,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from blink_call.modules.setting.setting_i18n import SETTING_I18N
from blink_call.modules.setting.setting_viewmodel import SettingViewModel


class SettingView(QWidget):
    popup_closed = Signal()

    def __init__(self, vm: SettingViewModel, parent=None):
        super().__init__(parent)
        self.vm = vm

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

        scroll_area = QScrollArea()
        scroll_area.setObjectName("settingScrollArea")
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        panel_layout.addWidget(scroll_area, 1)

        scroll_content = QWidget()
        scroll_content.setObjectName("settingScrollContent")
        scroll_area.setWidget(scroll_content)

        content_layout = QVBoxLayout(scroll_content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(16)

        general_group = QFrame()
        general_group.setObjectName("settingGeneralGroup")
        content_layout.addWidget(general_group)

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

        # General setting : UI language
        language_row = QHBoxLayout()
        self.language_label = QLabel("Language")
        self.language_combo = QComboBox()
        self.language_combo.addItem("\u4e2d\u6587", "zh")
        self.language_combo.addItem("English", "en")
        language_row.addWidget(self.language_label)
        language_row.addWidget(self.language_combo)
        language_row.addStretch()
        general_layout.addLayout(language_row)
        self.bind_combo(self.language_combo, "ui.language")

        camera_group = QFrame()
        camera_group.setObjectName("settingCameraGroup")
        content_layout.addWidget(camera_group)

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
        self.bind_spinbox(self.local_id, "camera.local_camera_id")

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
        self.bind_line_edit(self.remote_ip, "camera.remote.ip")
        self.bind_spinbox(self.remote_port, "camera.remote.port")

        radio_group = QButtonGroup(self)
        radio_group.addButton(self.local_radio)
        radio_group.addButton(self.remote_radio)
        self.local_radio.setProperty("tag_value", "local")
        self.remote_radio.setProperty("tag_value", "remote")
        self.bind_radio_group(radio_group, "camera.mode")

        other_group = QFrame()
        other_group.setObjectName("settingOtherGroup")
        content_layout.addWidget(other_group)

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
        self.bind_spinbox(self.service_camera_id, "local_service.camera_id")
        self.bind_spinbox(self.service_port, "local_service.port")

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

        content_layout.addStretch()

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save settings")
        self.save_btn.setObjectName("settingSaveBtn")
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("settingCloseBtn")
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.close_btn)
        panel_layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self.vm.save_config)
        self.close_btn.clicked.connect(self.vm.close)
        self.reset_btn.clicked.connect(self._restore_default)
        self.start_service_btn.clicked.connect(self._start_service)
        self.vm.close_requested.connect(self.hide)

        self.refresh_from_model()

    def bind_radio_group(self, group, path):
        def on_changed(btn):
            value = btn.property("tag_value")
            self.vm.set_config(path, value)

        group.buttonClicked.connect(on_changed)

    def bind_line_edit(self, edit, path: str):
        def on_changed(text):
            self.vm.set_config(path, text)

        edit.textChanged.connect(on_changed)

    def bind_combo(self, combo, path: str):
        def on_changed():
            self.vm.set_config(path, combo.currentData())

        combo.currentIndexChanged.connect(on_changed)

    def bind_spinbox(self, spinbox, path: str):
        def on_changed(value: int):
            self.vm.set_config(path, int(value))

        spinbox.valueChanged.connect(on_changed)

    def refresh_from_model(self):
        language_idx = self.language_combo.findData(self.vm.get_config("ui.language"))
        self.language_combo.blockSignals(True)
        self.language_combo.setCurrentIndex(0 if language_idx < 0 else language_idx)
        self.language_combo.blockSignals(False)
        self._apply_language()

        if self.vm.get_config("camera.mode") == "remote":
            self.remote_radio.setChecked(True)
        else:
            self.local_radio.setChecked(True)

        self.local_id.setValue(int(self.vm.get_config("camera.local_camera_id") or 0))
        self.remote_ip.setText(self.vm.get_config("camera.remote.ip") or "")
        self.remote_port.setValue(int(self.vm.get_config("camera.remote.port") or 10000))

        self.service_camera_id.setValue(int(self.vm.get_config("local_service.camera_id") or 0))
        self.service_port.setValue(int(self.vm.get_config("local_service.port") or 10000))

    def _apply_language(self):
        i18n = SETTING_I18N.get(self.vm.get_config("ui.language"), SETTING_I18N["zh"])

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

    def _start_service(self):
        self.vm.start_local_service_only()

    def _restore_default(self):
        i18n = SETTING_I18N.get(self.vm.model.get("ui.language"), self.TRANSLATIONS["zh"])
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setWindowTitle(i18n["confirm_reset_title"])
        msg.setText(i18n["confirm_reset_msg"])
        confirm_btn = msg.addButton(i18n["confirm_btn"], QMessageBox.ButtonRole.AcceptRole)
        msg.addButton(i18n["close_btn"], QMessageBox.ButtonRole.RejectRole)
        msg.exec()
        if msg.clickedButton() == confirm_btn:
            self.vm.restore_default_config()

    def showEvent(self, event):
        self.refresh_from_model()
        super().showEvent(event)

    def hideEvent(self, event):
        self.popup_closed.emit()
        super().hideEvent(event)
