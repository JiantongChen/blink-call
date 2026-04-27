from PySide6.QtWidgets import QFrame


class HDividerLine(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setObjectName("settingItemDivider")
        self.setFrameShape(QFrame.Shape.HLine)
        self.setFrameShadow(QFrame.Shadow.Plain)
        self.setLineWidth(1)
