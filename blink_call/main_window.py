from PySide6.QtWidgets import QStackedWidget, QVBoxLayout, QWidget

from blink_call.core.config_manager import ConfigManager


class MainWindow(QWidget):
    WINDOW_TITLE = {
        "zh": "\u7728\u773c\u547c\u53eb",
        "en": "Blink Call",
    }

    def __init__(self):
        super().__init__()
        language = self._load_ui_language()
        self.set_ui_language(language)
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)

        self.stack = QStackedWidget()
        self.views = {}

        layout = QVBoxLayout(self)
        layout.addWidget(self.stack)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

    @staticmethod
    def _load_ui_language():
        local_ui = ConfigManager.get_local_config().get("ui") or {}
        default_ui = ConfigManager.get_default_config().get("ui") or {}
        return local_ui.get("language", default_ui.get("language", "zh"))

    def set_ui_language(self, language):
        title_base = self.WINDOW_TITLE.get(language, self.WINDOW_TITLE["zh"])
        self.setWindowTitle(f"{title_base} v{self.get_version()}")

    def add_page(self, name, view):
        self.views[name] = view
        self.stack.addWidget(view)

    def navigate(self, name):
        view = self.views[name]
        vm = getattr(view, "vm", None)

        if hasattr(vm, "on_page_enter"):
            vm.on_page_enter()
        self.stack.setCurrentWidget(view)

    def closeEvent(self, event):
        for view in self.views.values():
            vm = getattr(view, "vm", None)
            if hasattr(vm, "stop_all"):
                vm.stop_all()
        super().closeEvent(event)

    @staticmethod
    def get_version():
        with open("VERSION", encoding="utf-8") as f:
            version = f.read().strip()

        return version
