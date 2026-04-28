from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from blink_call.widget import HDividerLine, NoWheelSpinBox


@dataclass
class CameraPageWidgets:
    choose_camera_source_label: QLabel
    camera_local_mode_radio: QRadioButton
    camera_remote_mode_radio: QRadioButton
    local_mode_widgets_row: QWidget
    local_camera_id_label: QLabel
    local_camera_id: NoWheelSpinBox
    remote_mode_widgets_row: QWidget
    remote_service_info_label: QLabel
    remote_ip_label: QLabel
    remote_ip: QLineEdit
    remote_port_label: QLabel
    remote_port: NoWheelSpinBox
    service_section_label: QLabel
    service_camera_id_label: QLabel
    service_camera_id: NoWheelSpinBox
    service_port_label: QLabel
    service_port: NoWheelSpinBox
    start_service_label: QLabel
    start_service_btn: QPushButton


def build_camera_page(content_stack: QStackedWidget) -> CameraPageWidgets:
    camera_scroll = QScrollArea()
    camera_scroll.setObjectName("settingRightScroll")
    camera_scroll.setWidgetResizable(True)
    camera_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    camera_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    camera_scroll.setFrameShape(QFrame.Shape.NoFrame)
    content_stack.addWidget(camera_scroll)

    camera_page = QFrame()
    camera_page.setObjectName("settingContentPage")
    camera_page.setMinimumWidth(550)
    camera_scroll.setWidget(camera_page)

    camera_layout = QVBoxLayout(camera_page)
    camera_layout.setContentsMargins(16, 16, 16, 16)
    camera_layout.setSpacing(16)

    source_row = QHBoxLayout()
    source_row.setSpacing(16)
    choose_camera_source_label = QLabel("Choose camera source:")
    choose_camera_source_label.setObjectName("settingSubSectionTitle")
    camera_local_mode_radio = QRadioButton("Local camera")
    camera_remote_mode_radio = QRadioButton("Remote camera")
    source_row.addWidget(choose_camera_source_label)
    source_row.addStretch()
    source_row.addWidget(camera_local_mode_radio)
    source_row.addWidget(camera_remote_mode_radio)
    camera_layout.addLayout(source_row)

    local_mode_widgets_row = QWidget()
    local_camera_id_row = QHBoxLayout(local_mode_widgets_row)
    local_camera_id_row.setContentsMargins(0, 0, 0, 0)
    local_camera_id_row.setSpacing(16)
    local_camera_id_label = QLabel("ID")
    local_camera_id = NoWheelSpinBox()
    local_camera_id.setMinimum(0)
    local_camera_id.setMaximum(20)
    local_camera_id.setFixedWidth(120)
    local_camera_id_row.addWidget(local_camera_id_label)
    local_camera_id_row.addStretch()
    local_camera_id_row.addWidget(local_camera_id)
    camera_layout.addWidget(local_mode_widgets_row)

    remote_mode_widgets_row = QWidget()
    remote_layout = QHBoxLayout(remote_mode_widgets_row)
    remote_layout.setContentsMargins(0, 0, 0, 0)
    remote_layout.setSpacing(16)
    remote_service_info_label = QLabel("Remote")
    remote_ip_label = QLabel("IP")
    remote_ip = QLineEdit()
    remote_ip.setPlaceholderText("IP")
    remote_port_label = QLabel("Port")
    remote_port = NoWheelSpinBox()
    remote_port.setMinimum(1)
    remote_port.setMaximum(65535)
    remote_ip.setFixedWidth(140)
    remote_port.setFixedWidth(120)
    remote_layout.addWidget(remote_service_info_label)
    remote_layout.addStretch()
    remote_layout.addWidget(remote_ip_label)
    remote_layout.addWidget(remote_ip)
    remote_layout.addWidget(remote_port_label)
    remote_layout.addWidget(remote_port)
    camera_layout.addWidget(remote_mode_widgets_row)

    camera_layout.addWidget(HDividerLine())

    start_btn_row = QHBoxLayout()
    start_btn_row.setSpacing(16)
    start_service_label = QLabel("Start local camera service")
    start_service_label.setObjectName("settingSubSectionTitle")
    start_service_btn = QPushButton("Start local camera service")
    start_service_btn.setObjectName("settingStartServiceBtn")
    start_service_btn.setFixedWidth(260)
    start_btn_row.addWidget(start_service_label)
    start_btn_row.addStretch()
    start_btn_row.addWidget(start_service_btn)
    camera_layout.addLayout(start_btn_row)

    service_cfg_row = QHBoxLayout()
    service_cfg_row.setSpacing(16)
    service_section_label = QLabel("Local service config")
    service_camera_id_label = QLabel("Service ID")
    service_camera_id = NoWheelSpinBox()
    service_camera_id.setMinimum(0)
    service_camera_id.setMaximum(20)
    service_camera_id.setFixedWidth(120)
    service_port_label = QLabel("Service Port")
    service_port = NoWheelSpinBox()
    service_port.setMinimum(1)
    service_port.setMaximum(65535)
    service_port.setFixedWidth(120)
    service_cfg_row.addWidget(service_section_label)
    service_cfg_row.addStretch()
    service_cfg_row.addWidget(service_camera_id_label)
    service_cfg_row.addWidget(service_camera_id)
    service_cfg_row.addWidget(service_port_label)
    service_cfg_row.addWidget(service_port)
    camera_layout.addLayout(service_cfg_row)
    camera_layout.addWidget(HDividerLine())
    camera_layout.addStretch()

    return CameraPageWidgets(
        choose_camera_source_label=choose_camera_source_label,
        camera_local_mode_radio=camera_local_mode_radio,
        camera_remote_mode_radio=camera_remote_mode_radio,
        local_mode_widgets_row=local_mode_widgets_row,
        local_camera_id_label=local_camera_id_label,
        local_camera_id=local_camera_id,
        remote_mode_widgets_row=remote_mode_widgets_row,
        remote_service_info_label=remote_service_info_label,
        remote_ip_label=remote_ip_label,
        remote_ip=remote_ip,
        remote_port_label=remote_port_label,
        remote_port=remote_port,
        service_section_label=service_section_label,
        service_camera_id_label=service_camera_id_label,
        service_camera_id=service_camera_id,
        service_port_label=service_port_label,
        service_port=service_port,
        start_service_label=start_service_label,
        start_service_btn=start_service_btn,
    )
