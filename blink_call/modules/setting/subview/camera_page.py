from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from blink_call.widget import HDividerLine, NoWheelSpinBox


class CameraPage:
    def __init__(self, content_stack):
        scroll = QScrollArea()
        scroll.setObjectName("settingRightScroll")
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content_stack.addWidget(scroll)

        page = QFrame()
        page.setObjectName("settingContentPage")
        page.setMinimumWidth(650)
        scroll.setWidget(page)

        layout = QVBoxLayout(page)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        source_row = QHBoxLayout()
        source_row.setSpacing(16)
        self.source_label = QLabel("Choose camera source:")
        self.source_label.setObjectName("settingSubSectionTitle")
        self.local_mode_radio = QRadioButton("Local camera")
        self.remote_mode_radio = QRadioButton("Remote camera")
        source_row.addWidget(self.source_label)
        source_row.addStretch()
        source_row.addWidget(self.local_mode_radio)
        source_row.addWidget(self.remote_mode_radio)
        layout.addLayout(source_row)

        self.local_row = QWidget()
        local_id_row = QHBoxLayout(self.local_row)
        local_id_row.setContentsMargins(0, 0, 0, 0)
        local_id_row.setSpacing(16)
        self.local_id_label = QLabel("ID")
        self.local_id_spin = NoWheelSpinBox()
        self.local_id_spin.setMinimum(0)
        self.local_id_spin.setMaximum(20)
        self.local_id_spin.setFixedWidth(90)
        local_id_row.addWidget(self.local_id_label)
        local_id_row.addStretch()
        local_id_row.addWidget(self.local_id_spin)
        layout.addWidget(self.local_row)

        self.remote_row = QWidget()
        remote_layout = QHBoxLayout(self.remote_row)
        remote_layout.setContentsMargins(0, 0, 0, 0)
        remote_layout.setSpacing(16)
        self.remote_info_label = QLabel("Remote")
        self.remote_ip_label = QLabel("IP")
        self.remote_ip_edit = QLineEdit()
        self.remote_ip_edit.setPlaceholderText("IP")
        self.remote_port_label = QLabel("Port")
        self.remote_port_spin = NoWheelSpinBox()
        self.remote_port_spin.setMinimum(1)
        self.remote_port_spin.setMaximum(65535)
        self.remote_ip_edit.setFixedSize(140, 40)
        remote_layout.addWidget(self.remote_info_label)
        remote_layout.addStretch()
        remote_layout.addWidget(self.remote_ip_label)
        remote_layout.addWidget(self.remote_ip_edit)
        remote_layout.addWidget(self.remote_port_label)
        remote_layout.addWidget(self.remote_port_spin)
        layout.addWidget(self.remote_row)

        layout.addWidget(HDividerLine())

        start_btn_row = QHBoxLayout()
        start_btn_row.setSpacing(16)
        self.start_label = QLabel("Start local camera service")
        self.start_label.setObjectName("settingSubSectionTitle")
        self.start_btn = QPushButton("Start local camera service")
        self.start_btn.setObjectName("settingStartServiceBtn")
        self.start_btn.setFixedSize(230, 36)
        start_btn_row.addWidget(self.start_label)
        start_btn_row.addStretch()
        start_btn_row.addWidget(self.start_btn)
        layout.addLayout(start_btn_row)

        service_cfg_row = QHBoxLayout()
        service_cfg_row.setSpacing(16)
        self.service_label = QLabel("Local service config")
        self.service_id_label = QLabel("Service ID")
        self.service_id_spin = NoWheelSpinBox()
        self.service_id_spin.setMinimum(0)
        self.service_id_spin.setMaximum(20)
        self.service_id_spin.setFixedWidth(90)
        self.service_port_label = QLabel("Service Port")
        self.service_port_spin = NoWheelSpinBox()
        self.service_port_spin.setMinimum(1)
        self.service_port_spin.setMaximum(65535)
        service_cfg_row.addWidget(self.service_label)
        service_cfg_row.addStretch()
        service_cfg_row.addWidget(self.service_id_label)
        service_cfg_row.addWidget(self.service_id_spin)
        service_cfg_row.addWidget(self.service_port_label)
        service_cfg_row.addWidget(self.service_port_spin)
        layout.addLayout(service_cfg_row)

        layout.addWidget(HDividerLine())
        layout.addStretch()
