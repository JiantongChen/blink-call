import json
import random
import re
import socket
from copy import deepcopy
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
import onnxruntime as ort
import yaml


class Helper:
    @classmethod
    def compare_versions(cls, version_a, version_b):
        def parse_version(version_str):
            version_text = str(version_str or "").strip()
            parts = [int(x) for x in re.findall(r"\d+", version_text)]
            return tuple(parts) if parts else (0,)

        a = parse_version(version_a)
        b = parse_version(version_b)
        max_len = max(len(a), len(b))
        a += (0,) * (max_len - len(a))
        b += (0,) * (max_len - len(b))
        if a < b:
            return -1
        if a > b:
            return 1
        return 0

    @classmethod
    def read_json(cls, path: Path, return_if_not_exists=None):
        if not path.exists():
            return return_if_not_exists

        with path.open("r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def write_json(
        cls,
        path: Path,
        data,
        ensure_ascii=False,
        indent=4,
    ):
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(
                data,
                f,
                ensure_ascii=ensure_ascii,
                indent=indent,
            )

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

    @classmethod
    def image_cropping(cls, image, bbox):
        if image is None or bbox is None:
            return None

        h, w = image.shape[:2]
        x1, y1, x2, y2 = bbox
        x1 = max(0, min(w - 1, x1))
        x2 = max(0, min(w - 1, x2))
        y1 = max(0, min(h - 1, y1))
        y2 = max(0, min(h - 1, y2))
        left, right = min(x1, x2), max(x1, x2)
        top, bottom = min(y1, y2), max(y1, y2)

        if right - left < 2 or bottom - top < 2:
            return None

        return image[top:bottom, left:right]

    @classmethod
    def points_to_bbox(cls, points, img_shape, padding=0):
        """
        Convert points to bbox with padding.
        """
        h, w = img_shape[:2]

        x_min = int(np.floor(np.min(points[:, 0]))) - padding
        y_min = int(np.floor(np.min(points[:, 1]))) - padding
        x_max = int(np.ceil(np.max(points[:, 0]))) + padding
        y_max = int(np.ceil(np.max(points[:, 1]))) + padding

        x_min = max(0, x_min)
        y_min = max(0, y_min)
        x_max = min(w - 1, x_max)
        y_max = min(h - 1, y_max)

        return [x_min, y_min, x_max, y_max]

    @classmethod
    def format_hms(cls, total_seconds: int):
        s = max(0, int(total_seconds))
        h = s // 3600
        m = (s % 3600) // 60
        sec = s % 60
        return f"{h:02d}:{m:02d}:{sec:02d}"

    @classmethod
    def create_ort_session(cls, onnx_path, ctx_id=0):
        def available_providers(ctx_id: int):
            available = ort.get_available_providers()
            if ctx_id >= 0 and "CUDAExecutionProvider" in available:
                return [
                    ("CUDAExecutionProvider", {"device_id": ctx_id}),
                    "CPUExecutionProvider",
                ]
            return ["CPUExecutionProvider"]

        options = ort.SessionOptions()
        options.intra_op_num_threads = 1
        options.inter_op_num_threads = 1
        options.execution_mode = ort.ExecutionMode.ORT_SEQUENTIAL
        options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        return ort.InferenceSession(
            str(onnx_path),
            sess_options=options,
            providers=available_providers(ctx_id),
        )
