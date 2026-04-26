from copy import deepcopy

from blink_call.core.config_manager import ConfigManager


class SettingModel:
    def __init__(self):
        self.local_config = None
        self.temp_config = None
        self.update_config_from_file()

    def update_config_from_file(self):
        self.local_config = ConfigManager.get_local_config()
        self.temp_config = deepcopy(self.local_config)

    def save_config(self):
        ConfigManager.update_local_config(self.temp_config)
        self.update_config_from_file()

    def restore_default_config(self):
        ConfigManager.reset_local_config_to_default()
        self.update_config_from_file()

    def get_config(self, path: str, source: str = "local"):
        keys = path.split(".")
        data = self.local_config if source == "local" else self.temp_config
        for k in keys:
            data = data[k]
        return data

    def set_config(self, path: str, value):
        keys = path.split(".")
        data = self.temp_config
        for k in keys[:-1]:
            data = data.setdefault(k, {})
        data[keys[-1]] = value
