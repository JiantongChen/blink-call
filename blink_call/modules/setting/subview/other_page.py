from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from blink_call.widget import HDividerLine, NoWheelSpinBox


class OtherPage:
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

        default_recording_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        if not default_recording_dir:
            default_recording_dir = str(Path.home() / "Desktop")

        self.recording_row = QWidget()
        recording_layout = QHBoxLayout(self.recording_row)
        recording_layout.setContentsMargins(0, 0, 0, 0)
        recording_layout.setSpacing(16)
        self.recording_label = QLabel("Current camera data recording")
        self.recording_label.setObjectName("settingSubSectionTitle")
        self.recording_btn = QPushButton("Start recording")
        self.recording_btn.setObjectName("settingStartRecordingBtn")
        self.recording_btn.setFixedWidth(230)
        recording_layout.addWidget(self.recording_label)
        recording_layout.addStretch()
        recording_layout.addWidget(self.recording_btn)
        layout.addWidget(self.recording_row)

        self.duration_row = QWidget()
        duration_layout = QHBoxLayout(self.duration_row)
        duration_layout.setContentsMargins(0, 0, 0, 0)
        duration_layout.setSpacing(12)
        self.duration_label = QLabel("Max duration")
        self.duration_label.setObjectName("settingSubSectionTitle")
        self.duration_spin = NoWheelSpinBox()
        self.duration_spin.setRange(1, 1440)
        self.duration_spin.setSingleStep(1)
        self.duration_spin.setDecimals(0)
        self.duration_unit_label = QLabel("min")
        self.duration_unit_label.setFixedWidth(40)
        duration_layout.addWidget(self.duration_label)
        duration_layout.addStretch()
        duration_layout.addWidget(self.duration_spin)
        duration_layout.addWidget(self.duration_unit_label)
        layout.addWidget(self.duration_row)

        self.path_row = QWidget()
        path_layout = QHBoxLayout(self.path_row)
        path_layout.setContentsMargins(0, 0, 0, 0)
        path_layout.setSpacing(12)
        self.path_label = QLabel("Local folder")
        self.path_label.setObjectName("settingSubSectionTitle")
        self.path_value_label = QLabel(default_recording_dir)
        self.path_btn = QPushButton("Choose folder")
        self.path_btn.setObjectName("settingNormalButton")
        self.path_btn.setFixedSize(160, 30)
        path_layout.addWidget(self.path_label)
        path_layout.addStretch()
        path_layout.addWidget(self.path_value_label)
        path_layout.addWidget(self.path_btn)
        layout.addWidget(self.path_row)

        layout.addWidget(HDividerLine())

        self.debug_row = QWidget()
        debug_layout = QHBoxLayout(self.debug_row)
        debug_layout.setContentsMargins(0, 0, 0, 0)
        debug_layout.setSpacing(16)
        self.debug_label = QLabel("Debug mode")
        self.debug_label.setObjectName("settingSubSectionTitle")
        self.debug_on_radio = QRadioButton("On")
        self.debug_off_radio = QRadioButton("Off")
        debug_layout.addWidget(self.debug_label)
        debug_layout.addStretch()
        debug_layout.addWidget(self.debug_on_radio)
        debug_layout.addWidget(self.debug_off_radio)
        layout.addWidget(self.debug_row)

        self.log_save_row = QWidget()
        log_save_layout = QHBoxLayout(self.log_save_row)
        log_save_layout.setContentsMargins(0, 0, 0, 0)
        log_save_layout.setSpacing(16)
        self.log_save_label = QLabel("Save to local file")
        self.log_save_label.setObjectName("settingSubSectionTitle")
        self.log_save_yes_radio = QRadioButton("Yes")
        self.log_save_no_radio = QRadioButton("No")
        log_save_layout.addWidget(self.log_save_label)
        log_save_layout.addStretch()
        log_save_layout.addWidget(self.log_save_yes_radio)
        log_save_layout.addWidget(self.log_save_no_radio)
        layout.addWidget(self.log_save_row)

        self.log_path_row = QWidget()
        log_path_layout = QHBoxLayout(self.log_path_row)
        log_path_layout.setContentsMargins(0, 0, 0, 0)
        log_path_layout.setSpacing(16)
        self.log_path_label = QLabel("Local file path")
        self.log_path_label.setObjectName("settingSubSectionTitle")
        self.log_path_value_label = QLabel("")
        self.log_path_btn = QPushButton("Choose folder")
        self.log_path_btn.setObjectName("settingNormalButton")
        self.log_path_btn.setFixedSize(160, 30)
        log_path_layout.addWidget(self.log_path_label)
        log_path_layout.addStretch()
        log_path_layout.addWidget(self.log_path_value_label)
        log_path_layout.addWidget(self.log_path_btn)
        layout.addWidget(self.log_path_row)

        layout.addWidget(HDividerLine())

        reset_layout = QHBoxLayout()
        reset_layout.setSpacing(16)
        self.reset_label = QLabel("Restore defaults")
        self.reset_label.setObjectName("settingSubSectionTitle")
        self.reset_btn = QPushButton("Restore defaults")
        self.reset_btn.setObjectName("settingResetBtn")
        self.reset_btn.setFixedSize(230, 36)
        reset_layout.addWidget(self.reset_label)
        reset_layout.addStretch()
        reset_layout.addWidget(self.reset_btn)
        layout.addLayout(reset_layout)

        layout.addWidget(HDividerLine())
        layout.addStretch()
