from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)
from PySide6.QtGui import QPixmap

from blink_call.modules.setting.subview import build_camera_page, build_general_page, build_other_page
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

        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        panel_layout.addLayout(content_layout, 1)

        left_nav_scroll = QScrollArea()
        left_nav_scroll.setObjectName("settingLeftScroll")
        left_nav_scroll.setWidgetResizable(True)
        left_nav_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_nav_scroll.setFrameShape(QFrame.Shape.NoFrame)
        left_nav_scroll.setFixedWidth(160)
        content_layout.addWidget(left_nav_scroll)

        left_nav = QFrame()
        left_nav.setObjectName("settingLeftNav")
        left_nav_scroll.setWidget(left_nav)

        left_nav_layout = QVBoxLayout(left_nav)
        left_nav_layout.setContentsMargins(12, 12, 12, 12)
        left_nav_layout.setSpacing(12)

        self.general_nav_row, self.general_nav_btn, self.general_nav_icon = self._create_nav_item("General")
        self.camera_nav_row, self.camera_nav_btn, self.camera_nav_icon = self._create_nav_item("Camera")
        self.other_nav_row, self.other_nav_btn, self.other_nav_icon = self._create_nav_item("Others")

        setting_pixmap = QPixmap("assets/icons/setting.png").scaled(
            25, 25,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.general_nav_icon.setPixmap(setting_pixmap)
        camera_pixmap = QPixmap("assets/icons/camera.png").scaled(
            25, 25,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.camera_nav_icon.setPixmap(camera_pixmap)
        others_pixmap = QPixmap("assets/icons/others.png").scaled(
            25, 25,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )
        self.other_nav_icon.setPixmap(others_pixmap)

        self.nav_rows = [self.general_nav_row, self.camera_nav_row, self.other_nav_row]
        self.nav_icons = [self.general_nav_icon, self.camera_nav_icon, self.other_nav_icon]

        left_nav_layout.addWidget(self.general_nav_row)
        left_nav_layout.addWidget(self.camera_nav_row)
        left_nav_layout.addWidget(self.other_nav_row)
        left_nav_layout.addStretch()

        nav_group = QButtonGroup(self)
        nav_group.setExclusive(True)
        nav_group.addButton(self.general_nav_btn, 0)
        nav_group.addButton(self.camera_nav_btn, 1)
        nav_group.addButton(self.other_nav_btn, 2)
        nav_group.idClicked.connect(self._switch_page)

        vline = QFrame()
        vline.setObjectName("settingCenterDivider")
        vline.setFrameShape(QFrame.Shape.VLine)
        content_layout.addWidget(vline)

        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("settingContentStack")
        content_layout.addWidget(self.content_stack, 1)

        self._attach_widgets(build_general_page(self.content_stack))
        self._attach_widgets(build_camera_page(self.content_stack))
        self._attach_widgets(build_other_page(self.content_stack))

        self.bind_combo(self.language_combo, "ui.language")
        self.bind_spinbox(self.local_id, "camera.local_camera_id")
        self.bind_line_edit(self.remote_ip, "camera.remote.ip")
        self.bind_spinbox(self.remote_port, "camera.remote.port")
        self.bind_spinbox(self.service_camera_id, "local_service.camera_id")
        self.bind_spinbox(self.service_port, "local_service.port")

        radio_group = QButtonGroup(self)
        radio_group.addButton(self.local_radio)
        radio_group.addButton(self.remote_radio)
        self.local_radio.setProperty("tag_value", "local")
        self.remote_radio.setProperty("tag_value", "remote")
        self.bind_radio_group(radio_group, "camera.mode")

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

        self.general_nav_btn.setChecked(True)
        self.content_stack.setCurrentIndex(0)
        self._update_nav_styles(0)
        self.refresh_from_model()

    def _create_nav_item(self, text: str):
        row = QWidget()
        row.setObjectName("settingNavRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 10, 10, 10)
        row_layout.setSpacing(5)

        icon_slot = QLabel()
        icon_slot.setObjectName("settingNavIconSlot")
        icon_slot.setFixedSize(25, 25)
        icon_slot.setAlignment(Qt.AlignCenter)
        row_layout.addWidget(icon_slot)

        btn = QPushButton(text)
        btn.setObjectName("settingNavBtn")
        btn.setCheckable(True)
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row_layout.addWidget(btn)
        return row, btn, icon_slot

    def _attach_widgets(self, page_widgets):
        for key, value in vars(page_widgets).items():
            setattr(self, key, value)

    def _switch_page(self, page_index: int):
        self.content_stack.setCurrentIndex(page_index)
        self._update_nav_styles(page_index)

    def _update_nav_styles(self, page_index: int):
        for idx, row in enumerate(self.nav_rows):
            row.setProperty("active", idx == page_index)
            row.style().unpolish(row)
            row.style().polish(row)

        for idx, icon in enumerate(self.nav_icons):
            icon.setProperty("active", idx == page_index)
            icon.style().unpolish(icon)
            icon.style().polish(icon)

    def bind_radio_group(self, group, path):
        def on_changed(btn):
            value = btn.property("tag_value")
            self.vm.set_config(path, value)
            if path == "camera.mode":
                self._update_camera_mode_visibility(value)

        group.buttonClicked.connect(on_changed)

    def _update_camera_mode_visibility(self, mode: str):
        is_local = mode != "remote"
        self.local_row.setVisible(is_local)
        self.remote_row.setVisible(not is_local)

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
            self._update_camera_mode_visibility("remote")
        else:
            self.local_radio.setChecked(True)
            self._update_camera_mode_visibility("local")

        self.local_id.setValue(int(self.vm.get_config("camera.local_camera_id") or 0))
        self.remote_ip.setText(self.vm.get_config("camera.remote.ip") or "")
        self.remote_port.setValue(int(self.vm.get_config("camera.remote.port") or 10000))

        self.service_camera_id.setValue(int(self.vm.get_config("local_service.camera_id") or 0))
        self.service_port.setValue(int(self.vm.get_config("local_service.port") or 10000))

    def _apply_language(self):
        i18n = SETTING_I18N.get(self.vm.get_config("ui.language"), SETTING_I18N["zh"])

        self.title_label.setText(i18n["title"])
        self.general_nav_btn.setText(i18n["general_title"])
        self.camera_nav_btn.setText(i18n["camera_title"])
        self.other_nav_btn.setText(i18n["other_title"])

        self.language_label.setText(i18n["language"])

        self.choose_label.setText(i18n["choose_label"])
        self.local_radio.setText(i18n["local_radio"])
        self.remote_radio.setText(i18n["remote_radio"])
        self.local_id_label.setText(i18n["local_id_label"])
        self.remote_title_label.setText(i18n["remote_address_label"])
        self.remote_ip_label.setText(i18n["ip_label"])
        self.remote_port_label.setText(i18n["port_label"])
        self.start_service_btn.setText(i18n["start_service_btn"])
        self.start_service_label.setText(i18n["service_section_title"])
        self.service_section_label.setText(i18n["remote_camera_service_config"])
        self.service_id_label.setText(i18n["local_id_label"])
        self.service_port_label.setText(i18n["port_label"])

        self.reset_btn.setText(i18n["reset_btn"])
        self.reset_label.setText(i18n["reset_btn"])

        self.save_btn.setText(i18n["save_btn"])
        self.close_btn.setText(i18n["close_btn"])

    def _start_service(self):
        self.vm.start_local_service_only()

    def _restore_default(self):
        i18n = SETTING_I18N.get(self.vm.get_config("ui.language"), SETTING_I18N["zh"])
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
