from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QWidget


class BlinkPatternProgressBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pattern = []
        self._progress_ratio = 0.0
        self.setMinimumHeight(25)

    def set_pattern(self, pattern):
        normalized = []
        for item in pattern if isinstance(pattern, list) else []:
            if not isinstance(item, dict):
                continue
            state = item.get("state")
            if state not in {"open", "closed"}:
                continue
            try:
                duration_s = float(item.get("duration_s"))
            except (TypeError, ValueError):
                continue
            if duration_s <= 0:
                continue
            normalized.append({"state": state, "duration_s": duration_s})

        self._pattern = normalized
        self.update()

    def set_progress_ratio(self, ratio):
        self._progress_ratio = min(1.0, max(0.0, float(ratio)))
        self.update()

    def paintEvent(self, event):
        super().paintEvent(event)
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
        if rect.width() <= 1 or rect.height() <= 1:
            return

        border_width = 2.0
        radius = rect.height() / 2.0

        painter.save()
        painter.setPen(QPen(QColor(0, 0, 0), border_width))
        painter.setBrush(QColor(240, 240, 240))
        painter.drawRoundedRect(rect, radius, radius)
        painter.restore()

        content_rect = rect.adjusted(border_width / 2.0, border_width / 2.0, -border_width / 2.0, -border_width / 2.0)
        content_radius = max(0.0, radius - border_width / 2.0)

        painter.save()
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setClipPath(self._rounded_path(content_rect, content_radius))

        if not self._pattern:
            painter.fillRect(content_rect, QColor(230, 230, 230))
            painter.restore()
            return

        total_duration = sum(float(item["duration_s"]) for item in self._pattern)
        if total_duration <= 0:
            painter.fillRect(content_rect, QColor(230, 230, 230))
            painter.restore()
            return

        x = float(content_rect.left())
        width = float(content_rect.width())
        height = float(content_rect.height())

        segment_boundaries = []
        for item in self._pattern:
            seg_ratio = float(item["duration_s"]) / total_duration
            seg_width = width * seg_ratio
            seg_rect = QRectF(x, float(content_rect.top()), seg_width, height)

            if item["state"] == "closed":
                seg_color = QColor(255, 251, 211)  # light yellow
            else:
                seg_color = QColor(211, 255, 218)  # light green

            painter.fillRect(seg_rect, seg_color)
            segment_boundaries.append(x)
            x += seg_width
        segment_boundaries.append(float(content_rect.right()))

        progress_w = width * self._progress_ratio
        if progress_w > 0:
            painter.fillRect(
                QRectF(float(content_rect.left()), float(content_rect.top()), progress_w, height),
                QColor(46, 125, 50, 200),
            )

        painter.setPen(QPen(QColor(150, 150, 150), 1))
        for boundary_x in segment_boundaries[1:-1]:
            painter.drawLine(boundary_x, content_rect.top(), boundary_x, content_rect.bottom())

        painter.restore()

    def _rounded_path(self, rect, radius):
        path = QPainterPath()
        path.addRoundedRect(rect, radius, radius)
        return path
