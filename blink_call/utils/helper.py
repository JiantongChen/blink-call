import random
import socket
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml

LOCAL_CONFIG_PATH = "configs/local_config.yaml"
DEFAULT_CONFIG_PATH = "configs/default_config.yaml"


class Helper:
    @classmethod
    def _read_yaml(cls, path: Path):
        if not path.exists():
            return {}

        with path.open(encoding="utf-8") as f:
            local_config = yaml.safe_load(f) or {}

        return local_config

    @classmethod
    def _write_yaml(cls, path: Path, data):
        path.parent.mkdir(parents=True, exist_ok=True)
        with NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            delete=False,
            suffix=".tmp",
        ) as f:
            yaml.safe_dump(data or {}, f, allow_unicode=True, sort_keys=False)
            tmp_path = Path(f.name)
        tmp_path.replace(path)

    @classmethod
    def _deep_merge_dict(cls, base: dict, patch: dict):
        result = deepcopy(base)
        for key, value in (patch or {}).items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = cls._deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def get_default_config(cls):
        return cls._read_yaml(Path(DEFAULT_CONFIG_PATH))

    @classmethod
    def get_local_config(cls):
        path = Path(LOCAL_CONFIG_PATH)
        if path.exists():
            return cls._read_yaml(path)

        default_config = cls.get_default_config()
        cls.save_local_config(default_config)
        return default_config

    @classmethod
    def save_local_config(cls, local_config):
        cls._write_yaml(Path(LOCAL_CONFIG_PATH), local_config)

    @classmethod
    def update_local_config(cls, patch):
        current = cls.get_local_config()
        merged = cls._deep_merge_dict(current, patch or {})
        cls.save_local_config(merged)
        return merged

    @classmethod
    def reset_local_config_to_default(cls):
        default_config = deepcopy(cls.get_default_config())
        cls.save_local_config(default_config)
        return default_config

    @classmethod
    def get_available_port(cls):
        while True:
            _port = random.randrange(10000, 65536)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                _flag = s.connect_ex(("0.0.0.0", _port)) != 0

            if _flag:
                return _port
