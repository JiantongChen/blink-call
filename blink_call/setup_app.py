import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from blink_call.core.di import DI
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
    theme.load("light.qss")

    # Initialize the main window
    main_window = MainWindow()
    nav = Navigation(main_window)

    # Add pages
    create_page("home", main_window, nav)

    # Default page
    nav.to("home")

    return app, main_window


if __name__ == "__main__":
    app, window = create_app()
    window.show()
    sys.exit(app.exec())
