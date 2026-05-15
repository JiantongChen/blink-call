from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from blink_call.widget import HDividerLine, NoWheelSpinBox


@dataclass
class OtherPageWidgets:
    recording_widgets_row: QWidget
    recording_label: QLabel
    recording_start_btn: QPushButton
    recording_duration_widgets_row: QWidget
    recording_duration_label: QLabel
    recording_duration_spin: NoWheelSpinBox
    recording_duration_unit_label: QLabel
    recording_path_widgets_row: QWidget
    recording_path_label: QLabel
    recording_path_value_label: QLabel
    recording_path_choose_btn: QPushButton
    debug_mode_widgets_row: QWidget
    debug_mode_label: QLabel
    debug_mode_on_radio: QRadioButton
    debug_mode_off_radio: QRadioButton
    debug_log_save_widgets_row: QWidget
    debug_log_save_label: QLabel
    debug_log_save_yes_radio: QRadioButton
    debug_log_save_no_radio: QRadioButton
    debug_log_path_widgets_row: QWidget
    debug_log_path_label: QLabel
    debug_log_path_value_label: QLabel
    debug_log_path_choose_btn: QPushButton
    reset_config_label: QLabel
    reset_config_btn: QPushButton


def build_other_page(content_stack: QStackedWidget) -> OtherPageWidgets:
    other_scroll = QScrollArea()
    other_scroll.setObjectName("settingRightScroll")
    other_scroll.setWidgetResizable(True)
    other_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    other_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    other_scroll.setFrameShape(QFrame.Shape.NoFrame)
    content_stack.addWidget(other_scroll)

    other_page = QFrame()
    other_page.setObjectName("settingContentPage")
    other_page.setMinimumWidth(650)
    other_scroll.setWidget(other_page)

    other_layout = QVBoxLayout(other_page)
    other_layout.setContentsMargins(16, 16, 16, 16)
    other_layout.setSpacing(16)

    default_recording_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
    if not default_recording_dir:
        default_recording_dir = str(Path.home() / "Desktop")

    recording_widgets_row = QWidget()
    recording_row = QHBoxLayout(recording_widgets_row)
    recording_row.setContentsMargins(0, 0, 0, 0)
    recording_row.setSpacing(16)
    recording_label = QLabel("Current camera data recording")
    recording_label.setObjectName("settingSubSectionTitle")
    recording_start_btn = QPushButton("Start recording")
    recording_start_btn.setObjectName("settingStartRecordingBtn")
    recording_start_btn.setFixedWidth(230)
    recording_row.addWidget(recording_label)
    recording_row.addStretch()
    recording_row.addWidget(recording_start_btn)
    other_layout.addWidget(recording_widgets_row)

    recording_duration_widgets_row = QWidget()
    recording_duration_row = QHBoxLayout(recording_duration_widgets_row)
    recording_duration_row.setContentsMargins(0, 0, 0, 0)
    recording_duration_row.setSpacing(12)
    recording_duration_label = QLabel("Max duration")
    recording_duration_label.setObjectName("settingSubSectionTitle")
    recording_duration_spin = NoWheelSpinBox()
    recording_duration_spin.setRange(1, 1440)
    recording_duration_spin.setSingleStep(1)
    recording_duration_spin.setDecimals(0)
    recording_duration_unit_label = QLabel("min")
    recording_duration_unit_label.setFixedWidth(40)
    recording_duration_row.addWidget(recording_duration_label)
    recording_duration_row.addStretch()
    recording_duration_row.addWidget(recording_duration_spin)
    recording_duration_row.addWidget(recording_duration_unit_label)
    other_layout.addWidget(recording_duration_widgets_row)

    recording_path_widgets_row = QWidget()
    recording_path_row = QHBoxLayout(recording_path_widgets_row)
    recording_path_row.setContentsMargins(0, 0, 0, 0)
    recording_path_row.setSpacing(12)
    recording_path_label = QLabel("Local folder")
    recording_path_label.setObjectName("settingSubSectionTitle")
    recording_path_value_label = QLabel(default_recording_dir)
    recording_path_choose_btn = QPushButton("Choose folder")
    recording_path_choose_btn.setObjectName("settingNormalButton")
    recording_path_choose_btn.setFixedSize(160, 30)
    recording_path_row.addWidget(recording_path_label)
    recording_path_row.addStretch()
    recording_path_row.addWidget(recording_path_value_label)
    recording_path_row.addWidget(recording_path_choose_btn)
    other_layout.addWidget(recording_path_widgets_row)

    other_layout.addWidget(HDividerLine())

    debug_mode_widgets_row = QWidget()
    debug_mode_row = QHBoxLayout(debug_mode_widgets_row)
    debug_mode_row.setContentsMargins(0, 0, 0, 0)
    debug_mode_row.setSpacing(16)
    debug_mode_label = QLabel("Debug mode")
    debug_mode_label.setObjectName("settingSubSectionTitle")
    debug_mode_on_radio = QRadioButton("On")
    debug_mode_off_radio = QRadioButton("Off")
    debug_mode_row.addWidget(debug_mode_label)
    debug_mode_row.addStretch()
    debug_mode_row.addWidget(debug_mode_on_radio)
    debug_mode_row.addWidget(debug_mode_off_radio)
    other_layout.addWidget(debug_mode_widgets_row)

    debug_log_save_widgets_row = QWidget()
    debug_log_save_row = QHBoxLayout(debug_log_save_widgets_row)
    debug_log_save_row.setContentsMargins(0, 0, 0, 0)
    debug_log_save_row.setSpacing(16)
    debug_log_save_label = QLabel("Save to local file")
    debug_log_save_label.setObjectName("settingSubSectionTitle")
    debug_log_save_yes_radio = QRadioButton("Yes")
    debug_log_save_no_radio = QRadioButton("No")
    debug_log_save_row.addWidget(debug_log_save_label)
    debug_log_save_row.addStretch()
    debug_log_save_row.addWidget(debug_log_save_yes_radio)
    debug_log_save_row.addWidget(debug_log_save_no_radio)
    other_layout.addWidget(debug_log_save_widgets_row)

    debug_log_path_widgets_row = QWidget()
    debug_log_path_row = QHBoxLayout(debug_log_path_widgets_row)
    debug_log_path_row.setContentsMargins(0, 0, 0, 0)
    debug_log_path_row.setSpacing(16)
    debug_log_path_label = QLabel("Local file path")
    debug_log_path_label.setObjectName("settingSubSectionTitle")
    debug_log_path_value_label = QLabel("")
    debug_log_path_choose_btn = QPushButton("Choose folder")
    debug_log_path_choose_btn.setObjectName("settingNormalButton")
    debug_log_path_choose_btn.setFixedSize(160, 30)
    debug_log_path_row.addWidget(debug_log_path_label)
    debug_log_path_row.addStretch()
    debug_log_path_row.addWidget(debug_log_path_value_label)
    debug_log_path_row.addWidget(debug_log_path_choose_btn)
    other_layout.addWidget(debug_log_path_widgets_row)

    other_layout.addWidget(HDividerLine())

    reset_config_btn_row = QHBoxLayout()
    reset_config_btn_row.setSpacing(16)
    reset_config_label = QLabel("Restore defaults")
    reset_config_label.setObjectName("settingSubSectionTitle")
    reset_config_btn = QPushButton("Restore defaults")
    reset_config_btn.setObjectName("settingResetBtn")
    reset_config_btn.setFixedSize(230, 36)
    reset_config_btn_row.addWidget(reset_config_label)
    reset_config_btn_row.addStretch()
    reset_config_btn_row.addWidget(reset_config_btn)
    other_layout.addLayout(reset_config_btn_row)

    other_layout.addWidget(HDividerLine())
    other_layout.addStretch()

    return OtherPageWidgets(
        recording_widgets_row=recording_widgets_row,
        recording_label=recording_label,
        recording_start_btn=recording_start_btn,
        recording_duration_widgets_row=recording_duration_widgets_row,
        recording_duration_label=recording_duration_label,
        recording_duration_spin=recording_duration_spin,
        recording_duration_unit_label=recording_duration_unit_label,
        recording_path_widgets_row=recording_path_widgets_row,
        recording_path_label=recording_path_label,
        recording_path_value_label=recording_path_value_label,
        recording_path_choose_btn=recording_path_choose_btn,
        debug_mode_widgets_row=debug_mode_widgets_row,
        debug_mode_label=debug_mode_label,
        debug_mode_on_radio=debug_mode_on_radio,
        debug_mode_off_radio=debug_mode_off_radio,
        debug_log_save_widgets_row=debug_log_save_widgets_row,
        debug_log_save_label=debug_log_save_label,
        debug_log_save_yes_radio=debug_log_save_yes_radio,
        debug_log_save_no_radio=debug_log_save_no_radio,
        debug_log_path_widgets_row=debug_log_path_widgets_row,
        debug_log_path_label=debug_log_path_label,
        debug_log_path_value_label=debug_log_path_value_label,
        debug_log_path_choose_btn=debug_log_path_choose_btn,
        reset_config_label=reset_config_label,
        reset_config_btn=reset_config_btn,
    )
