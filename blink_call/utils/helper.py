import random
import socket
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

import yaml


class Helper:
    @classmethod
    def read_yaml(cls, path: Path):
        if not path.exists():
            return {}

        with path.open(encoding="utf-8") as f:
            local_config = yaml.safe_load(f) or {}

        return local_config

    @classmethod
    def write_yaml(cls, path: Path, data):
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
    def deep_merge_dict(cls, base: dict, patch: dict):
        result = deepcopy(base)
        for key, value in (patch or {}).items():
            if isinstance(value, dict) and isinstance(result.get(key), dict):
                result[key] = cls.deep_merge_dict(result[key], value)
            else:
                result[key] = value
        return result

    @classmethod
    def get_available_port(cls, port=None):
        _port = port

        while True:
            if _port is None:
                _port = random.randrange(10000, 65536)
            else:
                _port += 1

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                _flag = s.connect_ex(("0.0.0.0", _port)) != 0

            if _flag:
                return _port

    @classmethod
    def get_local_ip(cls):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
        except OSError:
            return "127.0.0.1"
        finally:
            sock.close()
