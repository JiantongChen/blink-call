from dataclasses import dataclass

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QStackedWidget,
    QVBoxLayout,
)

from blink_call.widget import HDividerLine


@dataclass
class GeneralPageWidgets:
    user_manual_label: QLabel
    user_manual_btn: QPushButton
    language_label: QLabel
    language_combo: QComboBox
    theme_label: QLabel
    theme_combo: QComboBox


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
    general_page.setMinimumWidth(650)
    general_scroll.setWidget(general_page)

    general_layout = QVBoxLayout(general_page)
    general_layout.setContentsMargins(16, 16, 16, 16)
    general_layout.setSpacing(16)

    user_manual_row = QHBoxLayout()
    user_manual_row.setSpacing(16)
    user_manual_label = QLabel("User Manual")
    user_manual_label.setObjectName("settingSubSectionTitle")
    user_manual_btn = QPushButton("User Manual")
    user_manual_btn.setObjectName("settingUserManualBtn")
    user_manual_btn.setFixedSize(220, 36)

    user_manual_row.addWidget(user_manual_label)
    user_manual_row.addStretch()
    user_manual_row.addWidget(user_manual_btn)
    general_layout.addLayout(user_manual_row)

    general_layout.addWidget(HDividerLine())

    language_row = QHBoxLayout()
    language_row.setSpacing(16)
    language_label = QLabel("Language")
    language_label.setObjectName("settingSubSectionTitle")
    language_combo = QComboBox()
    language_combo.addItem("中文", "zh")
    language_combo.addItem("English", "en")
    language_combo.setFixedSize(220, 40)

    language_row.addWidget(language_label)
    language_row.addStretch()
    language_row.addWidget(language_combo)
    general_layout.addLayout(language_row)

    general_layout.addWidget(HDividerLine())

    theme_row = QHBoxLayout()
    theme_row.setSpacing(16)
    theme_label = QLabel("Theme")
    theme_label.setObjectName("settingSubSectionTitle")
    theme_combo = QComboBox()
    theme_combo.setFixedSize(220, 40)
    theme_combo.addItem("Light", "light")
    theme_combo.addItem("Dark", "dark")

    theme_row.addWidget(theme_label)
    theme_row.addStretch()
    theme_row.addWidget(theme_combo)
    general_layout.addLayout(theme_row)

    general_layout.addWidget(HDividerLine())
    general_layout.addStretch()

    return GeneralPageWidgets(
        user_manual_label=user_manual_label,
        user_manual_btn=user_manual_btn,
        language_label=language_label,
        language_combo=language_combo,
        theme_label=theme_label,
        theme_combo=theme_combo,
    )
