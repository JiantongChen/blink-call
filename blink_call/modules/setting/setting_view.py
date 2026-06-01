from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from blink_call.modules.i18n import get_i18n
from blink_call.modules.setting.controllers import (
    BlinkCallController,
    CameraController,
    GeneralController,
    OtherController,
)
from blink_call.modules.setting.setting_viewmodel import SettingViewModel
from blink_call.modules.setting.subview import (
    BlinkCallPage,
    CameraPage,
    GeneralPage,
    OtherPage,
)


class SettingView(QWidget):
    close_setting_popup = Signal()

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

        self.left_nav_layout = QVBoxLayout(left_nav)
        self.left_nav_layout.setContentsMargins(12, 12, 12, 12)
        self.left_nav_layout.setSpacing(12)

        self.nav_rows, self.nav_icons = [], []

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)
        self.nav_group.idClicked.connect(self.on_switch_setting_page)

        self.general_nav_btn = self._create_nav_item(0, "General", "assets/icons/setting.png")
        self.camera_nav_btn = self._create_nav_item(1, "Camera", "assets/icons/camera.png")
        self.blink_call_nav_btn = self._create_nav_item(2, "Blink Call", "assets/icons/algorithm.png")
        self.other_nav_btn = self._create_nav_item(3, "Others", "assets/icons/others.png")

        self.left_nav_layout.addStretch()

        vline = QFrame()
        vline.setObjectName("settingCenterDivider")
        vline.setFrameShape(QFrame.Shape.VLine)
        content_layout.addWidget(vline)

        self.content_stack = QStackedWidget()
        content_layout.addWidget(self.content_stack, 1)

        self.general_page = GeneralPage(self.content_stack)
        self.camera_page = CameraPage(self.content_stack)
        self.blink_call_page = BlinkCallPage(self.content_stack)
        self.other_page = OtherPage(self.content_stack)

        self.general_controller = GeneralController(self)
        self.camera_controller = CameraController(self)
        self.blink_call_controller = BlinkCallController(self)
        self.other_controller = OtherController(self)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save settings")
        self.save_btn.setObjectName("settingSaveBtn")
        self.save_btn.clicked.connect(self.vm.save_config)
        self.close_btn = QPushButton("Close")
        self.close_btn.setObjectName("settingCloseBtn")
        self.close_btn.clicked.connect(self.vm.close)
        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.close_btn)
        panel_layout.addLayout(btn_row)

        self.vm.close_requested.connect(self.hide)

        self.on_switch_setting_page(0)
        self.refresh_from_local_config()

    def _create_nav_item(self, idx: int, text: str, icon_path: str):
        row = QWidget()
        row.setObjectName("settingNavRow")
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(10, 10, 10, 10)
        row_layout.setSpacing(5)

        icon_slot = QLabel()
        icon_slot.setObjectName("settingNavIconSlot")
        icon_slot.setFixedSize(25, 25)
        icon_slot.setAlignment(Qt.AlignCenter)
        pixmap = QPixmap(icon_path).scaled(25, 25, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_slot.setPixmap(pixmap)
        row_layout.addWidget(icon_slot)

        btn = QPushButton(text)
        btn.setObjectName("settingNavBtn")
        btn.setCheckable(True)
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        row_layout.addWidget(btn)

        self.left_nav_layout.addWidget(row)
        self.nav_group.addButton(btn, idx)
        self.nav_rows.append(row)
        self.nav_icons.append(icon_slot)
        return btn

    def on_switch_setting_page(self, page_index: int):
        self.content_stack.setCurrentIndex(page_index)
        for idx, row in enumerate(self.nav_rows):
            row.setProperty("active", idx == page_index)
            row.style().unpolish(row)
            row.style().polish(row)

        for idx, icon in enumerate(self.nav_icons):
            icon.setProperty("active", idx == page_index)
            icon.style().unpolish(icon)
            icon.style().polish(icon)

    def refresh_from_local_config(self):
        i18n = get_i18n(self.vm.get_config("ui.language"))

        self.title_label.setText(i18n["setting"])
        self.general_nav_btn.setText(i18n["general"])
        self.camera_nav_btn.setText(i18n["camera"])
        self.blink_call_nav_btn.setText(i18n["blink_call"])
        self.other_nav_btn.setText(i18n["other"])
        self.save_btn.setText(i18n["save"])
        self.close_btn.setText(i18n["close"])

        self.general_controller.refresh_from_local_config()
        self.camera_controller.refresh_from_local_config()
        self.blink_call_controller.refresh_from_local_config()
        self.other_controller.refresh_from_local_config()

    def showEvent(self, event):
        self.refresh_from_local_config()
        self.vm.check_manual_update()
        super().showEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.blink_call_controller.on_host_resized()

    def hideEvent(self, event):
        self.blink_call_controller.stop_preview()
        self.close_setting_popup.emit()
        super().hideEvent(event)
