from PySide6.QtCore import QObject, Signal

from blink_call.modules.setting.setting_model import SettingModel


class SettingViewModel(QObject):
    close_requested = Signal()
    language_changed = Signal(str)
    save_setting = Signal()
    start_local_service = Signal()

    def __init__(self, model: SettingModel):
        super().__init__()
        self.model = model

    def set_config(self, path: str, value):
        self.model.set_config(path, value)

    def get_config(self, path: str, source: str = "local"):
        return self.model.get_config(path, source)

    def save_config(self):
        self.model.save_config()
        self.language_changed.emit(self.get_config("ui.language"))
        self.save_setting.emit()
        self.close_requested.emit()

    def close(self):
        self.model.update_config_from_file()
        self.language_changed.emit(self.get_config("ui.language"))
        self.close_requested.emit()

    def restore_default_config(self):
        self.model.restore_default_config()
        self.language_changed.emit(self.get_config("ui.language"))
        self.close_requested.emit()
        self.save_setting.emit()

    def on_start_local_service(self):
        self.close_requested.emit()
        self.start_local_service.emit()
