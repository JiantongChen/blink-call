import os


class ThemeManager:
    def __init__(self, app, qss_dir="assets/qss"):
        self.app = app
        self.qss_dir = qss_dir

    def load(self, filename):
        path = os.path.join(self.qss_dir, filename)
        with open(path, encoding="utf-8") as f:
            qss = f.read()
            self.app.setStyleSheet(qss)
