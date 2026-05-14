from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QProgressBar,
    QStyle,
    QStyleOptionProgressBar,
    QVBoxLayout,
    QWidget,
)


class AdaptiveTextProgressBar(QProgressBar):
    def paintEvent(self, event):
        option = QStyleOptionProgressBar()
        self.initStyleOption(option)
        option.textVisible = False

        painter = QPainter(self)
        self.style().drawControl(QStyle.ControlElement.CE_ProgressBar, option, painter, self)

        if self.maximum() <= self.minimum():
            return

        value = int(max(self.minimum(), min(self.maximum(), self.value())))
        ratio = (value - self.minimum()) / float(self.maximum() - self.minimum())
        filled_width = int(self.width() * ratio)

        text = f"{value}%"
        text_rect = self.rect()

        painter.setPen(QColor("#111827"))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)

        if filled_width > 0:
            painter.save()
            painter.setClipRect(0, 0, filled_width, self.height())
            painter.setPen(QColor("#ffffff"))
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, text)
            painter.restore()


class InteractionBlockOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._build_ui()
        self.show_block_only()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(24, 24, 24, 24)
        root.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_panel = QFrame(self)
        self.progress_panel.setObjectName("interactionOverlayPanel")
        panel_layout = QVBoxLayout(self.progress_panel)
        panel_layout.setContentsMargins(18, 16, 18, 16)
        panel_layout.setSpacing(10)

        self.progress_title = QLabel("", self.progress_panel)
        self.progress_title.setObjectName("interactionOverlayTitle")
        self.progress_title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.progress_bar = AdaptiveTextProgressBar(self.progress_panel)
        self.progress_bar.setObjectName("interactionOverlayProgress")
        self.progress_bar.setRange(0, 0)

        panel_layout.addWidget(self.progress_title)
        panel_layout.addWidget(self.progress_bar)
        root.addWidget(self.progress_panel)

    def show_block_only(self):
        self.progress_panel.hide()

    def show_progress(self, title, determinate=False):
        self.progress_title.setText(title or "")
        if determinate:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        else:
            self.progress_bar.setRange(0, 0)
        self.progress_panel.show()

    def set_progress(self, progress):
        if self.progress_bar.maximum() <= 0:
            self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(int(max(0, min(100, progress))))

    def set_title(self, title):
        self.progress_title.setText(title or "")

    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()
