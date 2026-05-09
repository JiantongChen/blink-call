from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from blink_call.widget import HDividerLine


@dataclass
class BlinkCallPageWidgets:
    blink_call_switch_widgets_row: QWidget
    blink_call_switch_label: QLabel
    blink_call_enabled_radio: QRadioButton
    blink_call_disabled_radio: QRadioButton
    blink_call_progress_widgets_row: QWidget
    blink_call_progress_label: QLabel
    blink_call_progress_show_radio: QRadioButton
    blink_call_progress_hide_radio: QRadioButton
    blink_call_switch_divider_line: HDividerLine
    blink_call_progress_divider_line: HDividerLine
    blink_call_sequence_label: QLabel
    blink_call_sequence_rows_host: QWidget
    blink_call_sequence_rows_layout: QVBoxLayout
    blink_call_add_sequence_btn: QPushButton
    blink_call_sequence_divider_line: HDividerLine
    blink_call_audio_enable_widgets_row: QWidget
    blink_call_audio_enable_label: QLabel
    blink_call_audio_enable_on_radio: QRadioButton
    blink_call_audio_enable_off_radio: QRadioButton
    blink_call_audio_enable_divider_line: HDividerLine
    blink_call_audio_file_widgets_row: QWidget
    blink_call_audio_file_label: QLabel
    blink_call_audio_file_combo: QComboBox
    blink_call_audio_preview_btn: QPushButton
    blink_call_audio_file_divider_line: HDividerLine
    blink_call_audio_volume_widgets_row: QWidget
    blink_call_audio_volume_label: QLabel
    blink_call_audio_volume_slider: QSlider
    blink_call_audio_volume_value_label: QLabel
    blink_call_audio_volume_divider_line: HDividerLine
    blink_call_audio_duration_widgets_row: QWidget
    blink_call_audio_duration_label: QLabel
    blink_call_audio_duration_combo: QComboBox
    blink_call_audio_duration_divider_line: HDividerLine


def build_blink_call_page(content_stack: QStackedWidget) -> BlinkCallPageWidgets:
    blink_call_scroll = QScrollArea()
    blink_call_scroll.setObjectName("settingRightScroll")
    blink_call_scroll.setWidgetResizable(True)
    blink_call_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    blink_call_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    blink_call_scroll.setFrameShape(QFrame.Shape.NoFrame)
    content_stack.addWidget(blink_call_scroll)

    blink_call_page = QFrame()
    blink_call_page.setObjectName("settingContentPage")
    blink_call_page.setMinimumWidth(550)
    blink_call_scroll.setWidget(blink_call_page)

    blink_call_layout = QVBoxLayout(blink_call_page)
    blink_call_layout.setContentsMargins(16, 16, 16, 16)
    blink_call_layout.setSpacing(16)

    blink_call_switch_widgets_row = QWidget()
    blink_call_switch_row = QHBoxLayout(blink_call_switch_widgets_row)
    blink_call_switch_row.setContentsMargins(0, 0, 0, 0)
    blink_call_switch_row.setSpacing(16)

    blink_call_switch_label = QLabel("Enable blink call")
    blink_call_switch_label.setObjectName("settingSubSectionTitle")
    blink_call_enabled_radio = QRadioButton("On")
    blink_call_disabled_radio = QRadioButton("Off")
    blink_call_switch_row.addWidget(blink_call_switch_label)
    blink_call_switch_row.addStretch()
    blink_call_switch_row.addWidget(blink_call_enabled_radio)
    blink_call_switch_row.addWidget(blink_call_disabled_radio)
    blink_call_layout.addWidget(blink_call_switch_widgets_row)

    blink_call_switch_divider_line = HDividerLine()
    blink_call_layout.addWidget(blink_call_switch_divider_line)

    blink_call_progress_widgets_row = QWidget()
    blink_call_progress_row = QHBoxLayout(blink_call_progress_widgets_row)
    blink_call_progress_row.setContentsMargins(0, 0, 0, 0)
    blink_call_progress_row.setSpacing(16)

    blink_call_progress_label = QLabel("Show top progress bar on home page")
    blink_call_progress_label.setObjectName("settingSubSectionTitle")
    blink_call_progress_show_radio = QRadioButton("Show")
    blink_call_progress_hide_radio = QRadioButton("Hide")
    blink_call_progress_row.addWidget(blink_call_progress_label)
    blink_call_progress_row.addStretch()
    blink_call_progress_row.addWidget(blink_call_progress_show_radio)
    blink_call_progress_row.addWidget(blink_call_progress_hide_radio)
    blink_call_layout.addWidget(blink_call_progress_widgets_row)

    blink_call_progress_divider_line = HDividerLine()
    blink_call_layout.addWidget(blink_call_progress_divider_line)

    sequence_title_row = QHBoxLayout()
    sequence_title_row.setContentsMargins(0, 0, 0, 0)
    sequence_title_row.setSpacing(16)
    blink_call_sequence_label = QLabel("Blink sequence")
    blink_call_sequence_label.setObjectName("settingSubSectionTitle")
    blink_call_add_sequence_btn = QPushButton("Add step")
    blink_call_add_sequence_btn.setFixedWidth(160)
    sequence_title_row.addWidget(blink_call_sequence_label)
    sequence_title_row.addStretch()
    sequence_title_row.addWidget(blink_call_add_sequence_btn)
    blink_call_layout.addLayout(sequence_title_row)

    blink_call_sequence_rows_host = QWidget()
    blink_call_sequence_rows_layout = QVBoxLayout(blink_call_sequence_rows_host)
    blink_call_sequence_rows_layout.setContentsMargins(0, 0, 0, 0)
    blink_call_sequence_rows_layout.setSpacing(8)
    blink_call_layout.addWidget(blink_call_sequence_rows_host)

    blink_call_sequence_divider_line = HDividerLine()
    blink_call_layout.addWidget(blink_call_sequence_divider_line)

    blink_call_audio_enable_widgets_row = QWidget()
    blink_call_audio_enable_row = QHBoxLayout(blink_call_audio_enable_widgets_row)
    blink_call_audio_enable_row.setContentsMargins(0, 0, 0, 0)
    blink_call_audio_enable_row.setSpacing(16)
    blink_call_audio_enable_label = QLabel("Play audio on call")
    blink_call_audio_enable_label.setObjectName("settingSubSectionTitle")
    blink_call_audio_enable_on_radio = QRadioButton("On")
    blink_call_audio_enable_off_radio = QRadioButton("Off")
    blink_call_audio_enable_row.addWidget(blink_call_audio_enable_label)
    blink_call_audio_enable_row.addStretch()
    blink_call_audio_enable_row.addWidget(blink_call_audio_enable_on_radio)
    blink_call_audio_enable_row.addWidget(blink_call_audio_enable_off_radio)
    blink_call_layout.addWidget(blink_call_audio_enable_widgets_row)

    blink_call_audio_enable_divider_line = HDividerLine()
    blink_call_layout.addWidget(blink_call_audio_enable_divider_line)

    blink_call_audio_file_widgets_row = QWidget()
    blink_call_audio_file_row = QHBoxLayout(blink_call_audio_file_widgets_row)
    blink_call_audio_file_row.setContentsMargins(0, 0, 0, 0)
    blink_call_audio_file_row.setSpacing(12)
    blink_call_audio_file_label = QLabel("Audio file")
    blink_call_audio_file_label.setObjectName("settingSubSectionTitle")
    blink_call_audio_file_combo = QComboBox()
    blink_call_audio_file_combo.setFixedWidth(180)
    blink_call_audio_preview_btn = QPushButton("Preview")
    blink_call_audio_preview_btn.setFixedWidth(120)
    blink_call_audio_file_row.addWidget(blink_call_audio_file_label)
    blink_call_audio_file_row.addStretch()
    blink_call_audio_file_row.addWidget(blink_call_audio_file_combo)
    blink_call_audio_file_row.addWidget(blink_call_audio_preview_btn)
    blink_call_layout.addWidget(blink_call_audio_file_widgets_row)

    blink_call_audio_file_divider_line = HDividerLine()
    blink_call_layout.addWidget(blink_call_audio_file_divider_line)

    blink_call_audio_volume_widgets_row = QWidget()
    blink_call_audio_volume_row = QHBoxLayout(blink_call_audio_volume_widgets_row)
    blink_call_audio_volume_row.setContentsMargins(0, 0, 0, 0)
    blink_call_audio_volume_row.setSpacing(12)
    blink_call_audio_volume_label = QLabel("Audio volume")
    blink_call_audio_volume_label.setObjectName("settingSubSectionTitle")
    blink_call_audio_volume_slider = QSlider(Qt.Orientation.Horizontal)
    blink_call_audio_volume_slider.setRange(0, 100)
    blink_call_audio_volume_slider.setSingleStep(1)
    blink_call_audio_volume_slider.setPageStep(5)
    blink_call_audio_volume_slider.setFixedWidth(220)
    blink_call_audio_volume_value_label = QLabel("100%")
    blink_call_audio_volume_value_label.setFixedWidth(52)
    blink_call_audio_volume_row.addWidget(blink_call_audio_volume_label)
    blink_call_audio_volume_row.addStretch()
    blink_call_audio_volume_row.addWidget(blink_call_audio_volume_slider)
    blink_call_audio_volume_row.addWidget(blink_call_audio_volume_value_label)
    blink_call_layout.addWidget(blink_call_audio_volume_widgets_row)

    blink_call_audio_volume_divider_line = HDividerLine()
    blink_call_layout.addWidget(blink_call_audio_volume_divider_line)

    blink_call_audio_duration_widgets_row = QWidget()
    blink_call_audio_duration_row = QHBoxLayout(blink_call_audio_duration_widgets_row)
    blink_call_audio_duration_row.setContentsMargins(0, 0, 0, 0)
    blink_call_audio_duration_row.setSpacing(12)
    blink_call_audio_duration_label = QLabel("Audio play duration")
    blink_call_audio_duration_label.setObjectName("settingSubSectionTitle")
    blink_call_audio_duration_combo = QComboBox()
    blink_call_audio_duration_combo.setFixedWidth(180)
    blink_call_audio_duration_row.addWidget(blink_call_audio_duration_label)
    blink_call_audio_duration_row.addStretch()
    blink_call_audio_duration_row.addWidget(blink_call_audio_duration_combo)
    blink_call_layout.addWidget(blink_call_audio_duration_widgets_row)

    blink_call_audio_duration_divider_line = HDividerLine()
    blink_call_layout.addWidget(blink_call_audio_duration_divider_line)
    blink_call_layout.addStretch()

    return BlinkCallPageWidgets(
        blink_call_switch_widgets_row=blink_call_switch_widgets_row,
        blink_call_switch_label=blink_call_switch_label,
        blink_call_enabled_radio=blink_call_enabled_radio,
        blink_call_disabled_radio=blink_call_disabled_radio,
        blink_call_progress_widgets_row=blink_call_progress_widgets_row,
        blink_call_progress_label=blink_call_progress_label,
        blink_call_progress_show_radio=blink_call_progress_show_radio,
        blink_call_progress_hide_radio=blink_call_progress_hide_radio,
        blink_call_switch_divider_line=blink_call_switch_divider_line,
        blink_call_progress_divider_line=blink_call_progress_divider_line,
        blink_call_sequence_label=blink_call_sequence_label,
        blink_call_sequence_rows_host=blink_call_sequence_rows_host,
        blink_call_sequence_rows_layout=blink_call_sequence_rows_layout,
        blink_call_add_sequence_btn=blink_call_add_sequence_btn,
        blink_call_sequence_divider_line=blink_call_sequence_divider_line,
        blink_call_audio_enable_widgets_row=blink_call_audio_enable_widgets_row,
        blink_call_audio_enable_label=blink_call_audio_enable_label,
        blink_call_audio_enable_on_radio=blink_call_audio_enable_on_radio,
        blink_call_audio_enable_off_radio=blink_call_audio_enable_off_radio,
        blink_call_audio_enable_divider_line=blink_call_audio_enable_divider_line,
        blink_call_audio_file_widgets_row=blink_call_audio_file_widgets_row,
        blink_call_audio_file_label=blink_call_audio_file_label,
        blink_call_audio_file_combo=blink_call_audio_file_combo,
        blink_call_audio_preview_btn=blink_call_audio_preview_btn,
        blink_call_audio_file_divider_line=blink_call_audio_file_divider_line,
        blink_call_audio_volume_widgets_row=blink_call_audio_volume_widgets_row,
        blink_call_audio_volume_label=blink_call_audio_volume_label,
        blink_call_audio_volume_slider=blink_call_audio_volume_slider,
        blink_call_audio_volume_value_label=blink_call_audio_volume_value_label,
        blink_call_audio_volume_divider_line=blink_call_audio_volume_divider_line,
        blink_call_audio_duration_widgets_row=blink_call_audio_duration_widgets_row,
        blink_call_audio_duration_label=blink_call_audio_duration_label,
        blink_call_audio_duration_combo=blink_call_audio_duration_combo,
        blink_call_audio_duration_divider_line=blink_call_audio_duration_divider_line,
    )
