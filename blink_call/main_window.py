from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"眨眼呼叫 v{self.get_version()}")
        self.resize(1200, 800)

        self.stack = QStackedWidget()
        self.views = {}

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    def add_page(self, name, view):
        self.views[name] = view
        self.stack.addWidget(view)

    def navigate(self, name):
        view = self.views[name]
        vm = getattr(view, "vm", None)

        if hasattr(vm, "on_page_enter"):
            vm.on_page_enter()
        self.stack.setCurrentWidget(view)

    @staticmethod
    def get_version():
        with open("VERSION", encoding="utf-8") as f:
            version = f.read().strip()

        return version
