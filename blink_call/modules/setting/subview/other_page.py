from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
)


@dataclass
class OtherPageWidgets:
    reset_label: QLabel
    reset_btn: QPushButton


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

    reset_btn_row = QHBoxLayout()
    reset_btn_row.setSpacing(16)
    reset_label = QLabel("Restore defaults")
    reset_label.setObjectName("settingSubSectionTitle")
    reset_btn = QPushButton("Restore defaults")
    reset_btn.setObjectName("settingResetBtn")
    reset_btn.setFixedWidth(260)
    reset_btn_row.addWidget(reset_label)
    reset_btn_row.addStretch()
    reset_btn_row.addWidget(reset_btn)
    other_layout.addLayout(reset_btn_row)

    divider = QFrame()
    divider.setObjectName("settingItemDivider")
    divider.setFrameShape(QFrame.Shape.HLine)
    other_layout.addWidget(divider)
    other_layout.addStretch()

    return OtherPageWidgets(reset_label=reset_label, reset_btn=reset_btn)
