from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QFrame, QHBoxLayout, QLabel, QScrollArea, QStackedWidget, QVBoxLayout


@dataclass
class GeneralPageWidgets:
    language_label: QLabel
    language_combo: QComboBox


def build_general_page(content_stack: QStackedWidget) -> GeneralPageWidgets:
    general_scroll = QScrollArea()
    general_scroll.setObjectName("settingRightScroll")
    general_scroll.setWidgetResizable(True)
    general_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    general_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
    general_scroll.setFrameShape(QFrame.Shape.NoFrame)
    content_stack.addWidget(general_scroll)

    general_page = QFrame()
    general_page.setObjectName("settingContentPage")
    general_page.setMinimumWidth(550)
    general_scroll.setWidget(general_page)

    general_layout = QVBoxLayout(general_page)
    general_layout.setContentsMargins(16, 16, 16, 16)
    general_layout.setSpacing(16)

    language_row = QHBoxLayout()
    language_row.setSpacing(16)
    language_label = QLabel("Language")
    language_label.setObjectName("settingSubSectionTitle")
    language_combo = QComboBox()
    language_combo.addItem("中文", "zh")
    language_combo.addItem("English", "en")
    language_combo.setFixedWidth(220)

    language_row.addWidget(language_label)
    language_row.addStretch()
    language_row.addWidget(language_combo)
    general_layout.addLayout(language_row)

    divider = QFrame()
    divider.setObjectName("settingItemDivider")
    divider.setFrameShape(QFrame.Shape.HLine)
    general_layout.addWidget(divider)
    general_layout.addStretch()

    return GeneralPageWidgets(language_label=language_label, language_combo=language_combo)
