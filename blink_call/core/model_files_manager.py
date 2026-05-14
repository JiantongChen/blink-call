import shutil
import threading
from enum import Enum
from pathlib import Path

from modelscope.hub import ProgressCallback
from modelscope.hub.api import HubApi
from modelscope.hub.snapshot_download import snapshot_download
from PySide6.QtCore import QObject, QStandardPaths, Signal
from requests.exceptions import ConnectionError, Timeout

from blink_call.utils.helper import Helper

APP_DATA_LOCAL_PATH = Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)) / "blink_call"
MODEL_ID = "chenjiantong/blink_call_model_files"
REPO_NAME = "blink_call_model_files"
MODEL_INFO_FILE = "model_info.json"
REQUIRED_MODEL_FILES = (
    ("ViTA", "eye_state_classification.onnx"),
    ("ViTA", "eye_state_classification.json"),
    ("insightface", "models", "buffalo_s_sft", "2d106det.onnx"),
    ("insightface", "models", "buffalo_s_sft", "det_500m.onnx"),
)


class ModelFilesStatus(Enum):
    MISSING = "missing"
    TIMEOUT = "timeout"
    UP_TO_DATE = "up_to_date"
    UPDATE_AVAILABLE = "update_available"


class ModelFilesManager(QObject):
    status_changed = Signal(dict)
    download_started = Signal()
    download_progress = Signal(dict)
    download_finished = Signal(bool)

    def __init__(self):
        super().__init__()

        APP_DATA_LOCAL_PATH.mkdir(parents=True, exist_ok=True)

        self.repo_dir = APP_DATA_LOCAL_PATH / REPO_NAME
        self.model_info_file = self.repo_dir / MODEL_INFO_FILE
        self.required_model_files = [self.repo_dir / Path(*parts) for parts in REQUIRED_MODEL_FILES]
        self.required_model_files.append(self.model_info_file)

        self._is_downloading = False
        self._is_checking = False

    def local_repo_exists(self):
        return self.repo_dir.exists() and self.repo_dir.is_dir()

    def all_model_files_exists(self):
        for rel_path in self.required_model_files:
            if not rel_path.exists():
                return False
        return True

    def get_remote_model_info(self, timeout_s=10.0):
        try:
            api = HubApi(timeout=timeout_s)
            return api.get_model(MODEL_ID), "empty", ""
        except Timeout:
            return None, "model_files_status_timeout", ""
        except ConnectionError:
            return None, "model_files_status_network_error", ""
        except Exception as exc:
            return None, "model_files_status_request_error", str(exc)

    def start_check_status(self, timeout_s=10.0):
        if self._is_checking:
            return

        threading.Thread(target=self._check_status_worker, args=(timeout_s,), daemon=True).start()

    def _check_status_worker(self, timeout_s=10.0):
        try:
            self._is_checking = True
            self._emit_status("model_files_status_checking", "", False)

            if not self.local_repo_exists() or not self.all_model_files_exists():
                self._emit_status("model_files_status_missing", "", True)
                return

            remote_info, error_key, error_detail = self.get_remote_model_info(timeout_s=timeout_s)
            if remote_info is None:
                self._emit_status(error_key, error_detail, False)
                return

            local_info = Helper.read_json(self.model_info_file, return_if_not_exists={})

            if int(remote_info["LastUpdatedTime"]) > int(local_info["LastUpdatedTime"]):
                self._emit_status("model_files_status_update_available", "", True)
            else:
                self._emit_status("model_files_status_up_to_date", "", False)
        except Exception as exc:
            self._emit_status("model_files_status_request_error", str(exc), False)
        finally:
            self._is_checking = False

    def start_download_or_update(self, timeout_s=10.0):
        if self._is_downloading:
            return

        threading.Thread(target=self._download_worker, args=(timeout_s,), daemon=True).start()

    def _download_worker(self, timeout_s):
        try:
            self._is_downloading = True
            self.download_started.emit()
            if self.repo_dir.exists():
                shutil.rmtree(self.repo_dir, ignore_errors=True)

            remote_info, error_key, error_detail = self.get_remote_model_info(timeout_s=timeout_s)
            if remote_info is None:
                self.download_finished.emit(False)
                self._emit_status(error_key, error_detail, True)
                return

            snapshot_download(
                model_id=MODEL_ID,
                local_dir=str(self.repo_dir.resolve()),
                progress_callbacks=[self._build_file_progress_callback()],
            )
            Helper.write_json(self.model_info_file, remote_info)

            if not self.all_model_files_exists():
                raise RuntimeError("Model files download incomplete")

            self.download_finished.emit(True)
        except Exception as exc:
            self.download_finished.emit(False)
            self._emit_status("model_files_status_download_error", str(exc), True)
        finally:
            self._is_downloading = False

    def _build_file_progress_callback(self):
        manager = self

        class SingleFileProgressCallback(ProgressCallback):
            def __init__(self, filename: str, file_size: int):
                super().__init__(filename, file_size)
                self.downloaded_file_size = 0
                manager.download_progress.emit({"progress": 0, "filename": self.filename})

            def update(self, size: int):
                self.downloaded_file_size += int(max(0, size))
                progress = self.downloaded_file_size / self.file_size * 100
                manager.download_progress.emit({"progress": progress, "filename": self.filename})

            def end(self):
                manager.download_progress.emit({"progress": 100, "filename": self.filename})

        return SingleFileProgressCallback

    def _emit_status(self, statue_key, detail, button_enabled):
        self.status_changed.emit({"desc_key": statue_key, "reason_detail": detail, "button_enabled": button_enabled})
