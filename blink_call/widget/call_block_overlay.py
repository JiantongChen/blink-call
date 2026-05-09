from PySide6.QtWidgets import QWidget


class CallBlockOverlay(QWidget):
    def mousePressEvent(self, event):
        event.accept()

    def mouseReleaseEvent(self, event):
        event.accept()

    def mouseDoubleClickEvent(self, event):
        event.accept()
