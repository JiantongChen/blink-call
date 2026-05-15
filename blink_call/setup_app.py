import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from blink_call.core.config_manager import ConfigManager
from blink_call.core.dependency_injection import DI
from blink_call.core.navigation import Navigation
from blink_call.core.theme_manager import ThemeManager
from blink_call.main_window import MainWindow
from blink_call.modules import MODULES_REGISTRY


def create_page(name, main_window, nav):
    _module = MODULES_REGISTRY[name]

    # Dependency Injection
    DI.register(name + "_model", _module["model"]())
    DI.register(name + "_vm", _module["vm"](DI.get(name + "_model")))

    # Create views
    view = _module["view"](DI.get(name + "_vm"), nav)

    # Add pages
    main_window.add_page(name, view)


def create_app():
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon("assets/icons/eye.png"))

    # Load theme
    theme = ThemeManager(app)
    ui_config = ConfigManager.get_local_config().get("ui") or {}
    theme_name = str(ui_config.get("theme") or "light").strip().lower()
    if theme_name not in {"light", "dark"}:
        theme_name = "light"
    theme.load(f"{theme_name}.qss")

    # Initialize the main window
    main_window = MainWindow()
    nav = Navigation(main_window)

    # Add pages
    create_page("home", main_window, nav)
    DI.get("home_vm").setting_vm.language_changed.connect(main_window.set_ui_language)
    DI.get("home_vm").setting_vm.theme_changed.connect(
        lambda value: theme.load(f'{"dark" if str(value).lower() == "dark" else "light"}.qss')
    )

    # Default page
    nav.to("home")

    return app, main_window


if __name__ == "__main__":
    app, window = create_app()
    window.show()
    sys.exit(app.exec())
