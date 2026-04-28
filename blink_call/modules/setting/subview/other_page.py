from dataclasses import dataclass

from PySide6.QtCore import Qt
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

from blink_call.widget import HDividerLine


@dataclass
class OtherPageWidgets:
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
    other_page.setMinimumWidth(550)
    other_scroll.setWidget(other_page)

    other_layout = QVBoxLayout(other_page)
    other_layout.setContentsMargins(16, 16, 16, 16)
    other_layout.setSpacing(16)

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
    debug_log_path_choose_btn.setFixedWidth(160)
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
    reset_config_btn.setFixedWidth(260)
    reset_config_btn_row.addWidget(reset_config_label)
    reset_config_btn_row.addStretch()
    reset_config_btn_row.addWidget(reset_config_btn)
    other_layout.addLayout(reset_config_btn_row)

    other_layout.addWidget(HDividerLine())
    other_layout.addStretch()

    return OtherPageWidgets(
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
