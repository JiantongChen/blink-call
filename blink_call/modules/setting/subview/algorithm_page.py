from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QRadioButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from blink_call.widget import HDividerLine


@dataclass
class AlgorithmPageWidgets:
    algorithm_switch_widgets_row: QWidget
    algorithm_switch_label: QLabel
    algorithm_enabled_radio: QRadioButton
    algorithm_disabled_radio: QRadioButton


def build_algorithm_page(content_stack: QStackedWidget) -> AlgorithmPageWidgets:
    algorithm_scroll = QScrollArea()
    algorithm_scroll.setObjectName("settingRightScroll")
    algorithm_scroll.setWidgetResizable(True)
    algorithm_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    algorithm_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    algorithm_scroll.setFrameShape(QFrame.Shape.NoFrame)
    content_stack.addWidget(algorithm_scroll)

    algorithm_page = QFrame()
    algorithm_page.setObjectName("settingContentPage")
    algorithm_page.setMinimumWidth(550)
    algorithm_scroll.setWidget(algorithm_page)

    algorithm_layout = QVBoxLayout(algorithm_page)
    algorithm_layout.setContentsMargins(16, 16, 16, 16)
    algorithm_layout.setSpacing(16)

    algorithm_switch_widgets_row = QWidget()
    algorithm_switch_row = QHBoxLayout(algorithm_switch_widgets_row)
    algorithm_switch_row.setContentsMargins(0, 0, 0, 0)
    algorithm_switch_row.setSpacing(16)

    algorithm_switch_label = QLabel("Enable algorithm")
    algorithm_switch_label.setObjectName("settingSubSectionTitle")
    algorithm_enabled_radio = QRadioButton("On")
    algorithm_disabled_radio = QRadioButton("Off")

    algorithm_switch_row.addWidget(algorithm_switch_label)
    algorithm_switch_row.addStretch()
    algorithm_switch_row.addWidget(algorithm_enabled_radio)
    algorithm_switch_row.addWidget(algorithm_disabled_radio)
    algorithm_layout.addWidget(algorithm_switch_widgets_row)

    algorithm_layout.addWidget(HDividerLine())
    algorithm_layout.addStretch()

    return AlgorithmPageWidgets(
        algorithm_switch_widgets_row=algorithm_switch_widgets_row,
        algorithm_switch_label=algorithm_switch_label,
        algorithm_enabled_radio=algorithm_enabled_radio,
        algorithm_disabled_radio=algorithm_disabled_radio,
    )
