from PySide6.QtWidgets import QSpinBox

class NoWheelSpinBox(QSpinBox):
    def wheelEvent(self, event):
        event.ignore()