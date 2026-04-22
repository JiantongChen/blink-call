import random
import socket

import yaml

GLOBAL_CONFIG_PATH = "configs/global_config.yaml"


class Helper:
    @classmethod
    def get_global_config(cls):
        with open(GLOBAL_CONFIG_PATH, encoding="utf-8") as f:
            global_config = yaml.safe_load(f) or {}

        return global_config

    @classmethod
    def get_available_port():
        while True:
            _port = random.randrange(10000, 65536)

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                _flag = s.connect_ex(("0.0.0.0", _port)) != 0

            if _flag:
                return _port


Utils = Helper
