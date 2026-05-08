from PySide6.QtWidgets import QDoubleSpinBox


class NoWheelSpinBox(QDoubleSpinBox):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setDecimals(0)
        self.setFixedSize(120, 42)

    def wheelEvent(self, event):
        event.ignore()
