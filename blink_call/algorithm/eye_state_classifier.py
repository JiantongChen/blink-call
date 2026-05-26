import time
from enum import Enum
from pathlib import Path

import cv2
import numpy as np
from PySide6.QtCore import QStandardPaths

from blink_call.utils.helper import Helper

ViTA_ROOT_PATH = (
    Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    / "blink_call"
    / "blink_call_model_files"
    / "ViTA"
)


class EyeState(Enum):
    CLOSE = "closed"
    OPEN = "open"
    NOT_EXIST = "not_exist"
    NOT_SURE = "not_sure"
    UNKNOWN = "unknown"


class EyeStateClassifier:
    """
    ONNXRuntime eye-state classifier.

    Public output states stay compatible with the blink-call pipeline:
    "closed", "open", "not_exist", "not_sure", or "unknown".
    """

    def __init__(self, configs):
        self.confidence_thresh = float(configs.get("confidence_thresh", 0.5))

        self.init_metadata()
        self.load_model()

    def init_metadata(self):
        metadata_path = ViTA_ROOT_PATH / "eye_state_classification.json"
        metadata = Helper.read_json(metadata_path, {})

        self.class_names = metadata.get("class_names", [EyeState.CLOSE, EyeState.OPEN, EyeState.NOT_EXIST])
        self.input_name = metadata.get("input_name", "images")
        self.output_name = metadata.get("output_name", "logits")

        preprocess = metadata.get("preprocess", {})
        self.resize_wh = tuple(preprocess.get("resize", [128, 128]))
        self.mean = np.array(preprocess.get("mean", [0.485, 0.456, 0.406]), dtype=np.float32).reshape(1, 1, 3)
        self.std = np.array(preprocess.get("std", [0.229, 0.224, 0.225]), dtype=np.float32).reshape(1, 1, 3)

    def load_model(self):
        model_path = ViTA_ROOT_PATH / "eye_state_classification.onnx"
        self.session = None
        self.load_error = ""

        try:
            self.session = Helper.create_ort_session(str(model_path.resolve()), ctx_id=-1)
        except Exception as exc:
            self.load_error = str(exc)

    def classify(self, eye_roi):
        if eye_roi is None:
            return self._return_data(debug_info="eye roi is None")

        if self.session is None:
            return self._return_data(debug_info=f"load model error: {self.load_error}")

        started = time.perf_counter()
        try:
            image_batch = self._preprocess(eye_roi)

            logits = self.session.run([self.output_name], {self.input_name: image_batch})[0]
            logits = np.asarray(logits, dtype=np.float32)
            if logits.ndim == 2:
                logits = logits[0]
            if logits.ndim != 1 or logits.size == 0:
                raise ValueError(f"unexpected_logits_shape={tuple(logits.shape)}")

            pred_idx = int(np.argmax(logits))
            model_label = self.class_names[pred_idx] if pred_idx < len(self.class_names) else str(pred_idx)
            confidence = float(self._softmax(logits)[pred_idx])
            state = model_label if confidence > self.confidence_thresh else EyeState.NOT_SURE
            elapsed_ms = (time.perf_counter() - started) * 1000.0

            return self._return_data(
                state=state,
                confidence=confidence,
                debug_info=(
                    f"label={model_label}, confidence={confidence:.3f}, state={state}, elapsed_ms={elapsed_ms:.1f}"
                ),
            )
        except Exception as exc:
            return self._return_data(debug_info=f"inference_error: {exc}")

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

    def _return_data(self, state=EyeState.UNKNOWN, confidence=-1, debug_info=""):
        return {
            "timestamp_ms": int(time.time() * 1000),
            "state": state,
            "confidence": confidence,
            "debug_info": debug_info,
        }
