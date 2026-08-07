import json
import threading
from pathlib import Path
from urllib.request import Request, urlopen

from PySide6.QtCore import QObject, QStandardPaths, Signal

from blink_call.modules.setting.setting_model import SettingModel
from blink_call.utils.helper import Helper

LATEST_RELEASE_API = "https://api.github.com/repos/JouleEmbodiedAILab/blink-call/releases/latest"
VERSION_FILE = Path(__file__).resolve().parents[3] / "VERSION"
APP_DATA_ROOT = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "blink_call"


class SettingViewModel(QObject):
    close_requested = Signal()
    language_changed = Signal(str)
    theme_changed = Signal(str)
    save_setting = Signal()
    start_local_service = Signal()
    start_recording_requested = Signal()
    manual_link_text_changed = Signal(str)

    def __init__(self, model: SettingModel):
        super().__init__()
        self.model = model
        self._manual_checking = False
        APP_DATA_ROOT.mkdir(parents=True, exist_ok=True)
        self.cached_latest_version_path = APP_DATA_ROOT / "github_latest_release_version"

    def set_config(self, path: str, value):
        self.model.set_config(path, value)

    def get_config(self, path: str, source: str = "local"):
        return self.model.get_config(path, source)

    def save_config(self):
        self.model.save_config()
        self.language_changed.emit(self.get_config("ui.language"))
        self.theme_changed.emit(self.get_config("ui.theme"))
        self.save_setting.emit()
        self.close_requested.emit()

    def close(self):
        self.model.update_config_from_file()
        self.language_changed.emit(self.get_config("ui.language"))
        self.theme_changed.emit(self.get_config("ui.theme"))
        self.close_requested.emit()

    def restore_default_config(self):
        self.model.restore_default_config()
        self.language_changed.emit(self.get_config("ui.language"))
        self.theme_changed.emit(self.get_config("ui.theme"))
        self.close_requested.emit()
        self.save_setting.emit()

    def on_start_local_service(self):
        self.close_requested.emit()
        self.start_local_service.emit()

    def start_recording(self):
        self.model.save_config()
        self.language_changed.emit(self.get_config("ui.language"))
        self.theme_changed.emit(self.get_config("ui.theme"))
        self.close_requested.emit()
        self.start_recording_requested.emit()

    def check_manual_update(self):
        if self._manual_checking:
            return
        self._manual_checking = True
        threading.Thread(target=self._check_manual_update_worker, daemon=True).start()

    def _check_manual_update_worker(self):
        has_update = False
        latest_version = None
        try:
            current_version = VERSION_FILE.read_text(encoding="utf-8").strip()

            request = Request(LATEST_RELEASE_API, headers={"User-Agent": "blink-call"})
            with urlopen(request, timeout=5) as response:
                payload = json.loads(response.read().decode("utf-8"))
            latest_version = str(payload.get("tag_name", "999.999.999")).strip().removeprefix("v")

            has_update = Helper.compare_versions(current_version, latest_version) < 0
        except Exception:
            if self.cached_latest_version_path.exists():
                latest_version = self.cached_latest_version_path.read_text(encoding="utf-8").strip()
                has_update = Helper.compare_versions(current_version, latest_version) < 0
        finally:
            if has_update and latest_version:
                self.cached_latest_version_path.write_text(latest_version, encoding="utf-8")
                self.manual_link_text_changed.emit("user_manual_with_update")
            self._manual_checking = False
