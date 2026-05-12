import json
import time
from pathlib import Path

import cv2
import numpy as np


class EyeStateClassifier:
    """
    ONNXRuntime eye-state classifier.

    Public output states stay compatible with the blink-call pipeline:
    "closed", "open", or "unknown". The ViTA model's third class,
    "irrelevant", is intentionally mapped to "unknown".
    """

    DEFAULT_MODEL_NAME = "eye3_mixed_unknown_convnext_tiny_128_fp32.onnx"
    DEFAULT_METADATA_NAME = "eye3_mixed_unknown_convnext_tiny_128_fp32.json"
    VALID_STATES = {"closed", "open"}

    def __init__(self, configs):
        self.configs = configs or {}
        self.session = None
        self.load_error = None
        self.input_name = "images"
        self.output_name = "logits"
        self.class_names = ["closed", "open", "irrelevant"]
        self.resize_wh = (128, 128)
        self.mean = np.array([0.485, 0.456, 0.406], dtype=np.float32).reshape(1, 1, 3)
        self.std = np.array([0.229, 0.224, 0.225], dtype=np.float32).reshape(1, 1, 3)

        self._load_model()

    def classify(self, eye_roi):
        timestamp_ms = int(time.time() * 1000)
        if eye_roi is None:
            return {
                "timestamp_ms": timestamp_ms,
                "state": "unknown",
                "debug_info": "no_eye_roi",
            }

        if self.session is None:
            return {
                "timestamp_ms": timestamp_ms,
                "state": "unknown",
                "debug_info": self.load_error or "model_not_loaded",
            }

        started = time.perf_counter()
        try:
            image_batch = self._preprocess(eye_roi)
            output_names = [self.output_name] if self.output_name else None
            logits = self.session.run(output_names, {self.input_name: image_batch})[0]
            logits = np.asarray(logits, dtype=np.float32)
            if logits.ndim == 2:
                logits = logits[0]
            if logits.ndim != 1 or logits.size == 0:
                raise ValueError(f"unexpected_logits_shape={tuple(logits.shape)}")

            pred_idx = int(np.argmax(logits))
            model_label = (
                self.class_names[pred_idx]
                if pred_idx < len(self.class_names)
                else str(pred_idx)
            )
            state = model_label if model_label in self.VALID_STATES else "unknown"
            confidence = float(self._softmax(logits)[pred_idx])
            elapsed_ms = (time.perf_counter() - started) * 1000.0

            return {
                "timestamp_ms": int(time.time() * 1000),
                "state": state,
                "debug_info": (
                    f"label={model_label}, state={state}, "
                    f"confidence={confidence:.3f}, latency_ms={elapsed_ms:.1f}"
                ),
            }
        except Exception as exc:
            return {
                "timestamp_ms": int(time.time() * 1000),
                "state": "unknown",
                "debug_info": f"inference_error: {exc}",
            }

    def _load_model(self):
        try:
            import onnxruntime as ort

            metadata_path = self._resolve_metadata_path()
            metadata = self._load_metadata(metadata_path)
            self._apply_metadata(metadata)

            model_path = self._resolve_model_path(metadata, metadata_path)
            providers = self._resolve_providers(ort)
            self.session = ort.InferenceSession(str(model_path), providers=providers)

            inputs = self.session.get_inputs()
            outputs = self.session.get_outputs()
            if inputs:
                self.input_name = inputs[0].name
            if outputs:
                self.output_name = outputs[0].name
        except Exception as exc:
            self.session = None
            self.load_error = f"model_load_error: {exc}"

    def _resolve_metadata_path(self):
        configured = self.configs.get("metadata_path") or self.configs.get(
            "onnx_metadata_path"
        )
        if configured:
            return Path(configured).expanduser()

        project_root = Path(__file__).resolve().parents[2]
        return project_root / "ViTA" / "exports" / self.DEFAULT_METADATA_NAME

    def _resolve_model_path(self, metadata, metadata_path):
        configured = self.configs.get("model_path") or self.configs.get(
            "onnx_model_path"
        )
        if configured:
            return Path(configured).expanduser()

        onnx_path = metadata.get("onnx_path")
        if onnx_path:
            candidate = Path(onnx_path).expanduser()
            if candidate.is_absolute():
                return candidate

            relative_to_metadata_dir = metadata_path.parent / candidate
            if relative_to_metadata_dir.exists():
                return relative_to_metadata_dir

            relative_to_vita_dir = metadata_path.parent.parent / candidate
            if relative_to_vita_dir.exists():
                return relative_to_vita_dir

        return metadata_path.with_name(self.DEFAULT_MODEL_NAME)

    def _load_metadata(self, metadata_path):
        with metadata_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    def _apply_metadata(self, metadata):
        class_names = metadata.get("class_names")
        if isinstance(class_names, list) and class_names:
            self.class_names = [str(name) for name in class_names]

        input_name = metadata.get("input_name")
        if isinstance(input_name, str) and input_name:
            self.input_name = input_name

        output_name = metadata.get("output_name")
        if isinstance(output_name, str) and output_name:
            self.output_name = output_name

        preprocess = metadata.get("preprocess") or {}
        resize = preprocess.get("resize")
        if isinstance(resize, list) and len(resize) == 2:
            self.resize_wh = (int(resize[1]), int(resize[0]))

        mean = preprocess.get("mean")
        if isinstance(mean, list) and len(mean) == 3:
            self.mean = np.array(mean, dtype=np.float32).reshape(1, 1, 3)

        std = preprocess.get("std")
        if isinstance(std, list) and len(std) == 3:
            self.std = np.array(std, dtype=np.float32).reshape(1, 1, 3)

    def _resolve_providers(self, ort):
        configured = self.configs.get("providers")
        if isinstance(configured, str):
            configured = [configured]
        if configured:
            return configured

        available = set(ort.get_available_providers())
        return (
            ["CPUExecutionProvider"]
            if "CPUExecutionProvider" in available
            else list(available)
        )

    def _preprocess(self, eye_roi):
        if not hasattr(eye_roi, "shape") or eye_roi.size == 0:
            raise ValueError("empty_eye_roi")

        if eye_roi.ndim == 2:
            rgb = cv2.cvtColor(eye_roi, cv2.COLOR_GRAY2RGB)
        elif eye_roi.ndim == 3 and eye_roi.shape[2] == 4:
            rgb = cv2.cvtColor(eye_roi, cv2.COLOR_BGRA2RGB)
        elif eye_roi.ndim == 3 and eye_roi.shape[2] == 3:
            rgb = cv2.cvtColor(eye_roi, cv2.COLOR_BGR2RGB)
        else:
            raise ValueError(f"unexpected_eye_roi_shape={tuple(eye_roi.shape)}")

        rgb = cv2.resize(rgb, self.resize_wh, interpolation=cv2.INTER_AREA)
        image = rgb.astype(np.float32)
        if image.max(initial=0.0) > 1.0:
            image /= 255.0

        image = (image - self.mean) / self.std
        image = np.transpose(image, (2, 0, 1))[None, ...]
        return np.ascontiguousarray(image, dtype=np.float32)

    def _softmax(self, logits):
        shifted = logits - np.max(logits)
        exp = np.exp(shifted)
        return exp / np.sum(exp)
