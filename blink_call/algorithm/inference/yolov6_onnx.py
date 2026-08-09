import cv2
import numpy as np

from blink_call.utils.helper import Helper


class YOLOv6ONNX:
    """YOLOv6 ONNX face detector.

    ``detect`` returns ``(dets, landmarks)`` where ``dets`` has the shape
    ``[N, 5]`` (x1, y1, x2, y2, confidence).  The empty landmark array keeps
    the detector contract while face landmarks continue to be produced by HRNet.
    """

    def __init__(
        self,
        onnx_path,
        input_size=(640, 640),
        ctx_id=0,
        score_thresh=0.65,
        nms_thresh=0.45,
        class_id=0,
        max_detections=100,
    ):
        self.onnx_path = str(onnx_path)
        self.configured_input_size = tuple(input_size)  # (width, height)
        self.input_size = self.configured_input_size
        self.static_model_input_size = None
        self.input_size_overridden = False
        self.score_thresh = float(score_thresh)
        self.nms_thresh = float(nms_thresh)
        self.class_id = None if class_id is None else int(class_id)
        self.max_detections = int(max_detections)
        self.last_debug_info = ""
        self.last_unclipped_detections = np.zeros((0, 5), dtype=np.float32)

        self.session = Helper.create_ort_session(self.onnx_path, ctx_id)
        model_input = self.session.get_inputs()[0]
        self.input_name = model_input.name
        self.output_names = [output.name for output in self.session.get_outputs()]
        self.input_dtype = np.float16 if model_input.type == "tensor(float16)" else np.float32
        self._use_static_model_size_if_available(model_input.shape)
        self._set_debug_info()

    def _use_static_model_size_if_available(self, shape):
        if len(shape) != 4:
            raise RuntimeError(f"YOLOv6 expects a 4-D NCHW input, got {shape}")
        height, width = shape[2], shape[3]
        if isinstance(height, (int, np.integer)) and isinstance(width, (int, np.integer)):
            self.static_model_input_size = (int(width), int(height))
            self.input_size = self.static_model_input_size
            self.input_size_overridden = self.input_size != self.configured_input_size

    def _set_debug_info(self, **extra):
        values = {
            "yolov6_path": self.onnx_path,
            "configured_input_size": self.configured_input_size,
            "input_size": self.input_size,
            "outputs": self.output_names,
            "class_id": self.class_id,
            "score_thresh": self.score_thresh,
        }
        if self.input_size_overridden:
            values["input_size_override"] = (
                f"{self.configured_input_size}->{self.input_size} (static ONNX)"
            )
        values.update(extra)
        self.last_debug_info = ", ".join(f"{key}={value}" for key, value in values.items())

    def preprocess(self, image):
        if image is None or image.ndim != 3 or image.shape[2] != 3:
            raise ValueError("YOLOv6 input must be a BGR image with shape HxWx3")

        input_width, input_height = self.input_size
        original_height, original_width = image.shape[:2]
        scale = min(input_width / original_width, input_height / original_height)
        resized_width = max(1, int(round(original_width * scale)))
        resized_height = max(1, int(round(original_height * scale)))

        resized = cv2.resize(image, (resized_width, resized_height), interpolation=cv2.INTER_LINEAR)
        pad_x = (input_width - resized_width) // 2
        pad_y = (input_height - resized_height) // 2
        canvas = np.full((input_height, input_width, 3), 114, dtype=np.uint8)
        canvas[pad_y : pad_y + resized_height, pad_x : pad_x + resized_width] = resized

        # YOLOv6 is exported with RGB, CHW and [0, 1] floating-point input.
        blob = canvas[:, :, ::-1].transpose(2, 0, 1)
        blob = np.ascontiguousarray(blob, dtype=self.input_dtype) / self.input_dtype(255.0)
        return blob[None], {
            "scale": scale,
            "pad_x": pad_x,
            "pad_y": pad_y,
            "original_width": original_width,
            "original_height": original_height,
        }

    @staticmethod
    def _xywh_to_xyxy(boxes):
        converted = np.empty_like(boxes, dtype=np.float32)
        converted[:, 0] = boxes[:, 0] - boxes[:, 2] * 0.5
        converted[:, 1] = boxes[:, 1] - boxes[:, 3] * 0.5
        converted[:, 2] = boxes[:, 0] + boxes[:, 2] * 0.5
        converted[:, 3] = boxes[:, 1] + boxes[:, 3] * 0.5
        return converted

    @staticmethod
    def _nms(boxes, scores, iou_threshold):
        if boxes.shape[0] == 0:
            return np.empty(0, dtype=np.int64)

        x1, y1, x2, y2 = boxes.T
        areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
        order = scores.argsort()[::-1]
        kept = []
        while order.size:
            index = int(order[0])
            kept.append(index)
            if order.size == 1:
                break
            remaining = order[1:]
            intersection_width = np.maximum(
                0.0, np.minimum(x2[index], x2[remaining]) - np.maximum(x1[index], x1[remaining])
            )
            intersection_height = np.maximum(
                0.0, np.minimum(y2[index], y2[remaining]) - np.maximum(y1[index], y1[remaining])
            )
            intersection = intersection_width * intersection_height
            union = areas[index] + areas[remaining] - intersection
            iou = intersection / np.maximum(union, 1e-7)
            order = remaining[iou <= iou_threshold]
        return np.asarray(kept, dtype=np.int64)

    def _decode_raw_output(self, output):
        prediction = np.asarray(output)
        if prediction.ndim == 3:
            prediction = prediction[0]
        if prediction.ndim != 2:
            raise RuntimeError(f"Unsupported YOLOv6 output shape: {np.asarray(output).shape}")

        # Some exporters produce [1, 5 + classes, anchors].
        if prediction.shape[0] <= 256 and prediction.shape[1] > prediction.shape[0]:
            prediction = prediction.T
        if prediction.shape[1] < 6:
            raise RuntimeError(f"YOLOv6 raw output needs at least 6 columns, got {prediction.shape}")

        # A regular YOLOv6 row is [xywh, objectness, class scores].  This
        # fine-tuned face export also carries five (x, y) landmark pairs:
        # [xywh, landmarks10, objectness, class scores].  YOLOv6 emits a
        # constant objectness value of one, so locate that column and ignore
        # the optional landmarks (HRNet supplies the 98 points used upstream).
        objectness_candidates = []
        for column in range(4, prediction.shape[1] - 1):
            values = prediction[:, column]
            if np.all(np.isfinite(values)) and np.max(np.abs(values - 1.0)) < 1e-4:
                objectness_candidates.append(column)
        objectness_index = objectness_candidates[-1] if objectness_candidates else 4
        objectness = prediction[:, objectness_index]
        class_scores = prediction[:, objectness_index + 1 :]
        if class_scores.shape[1] == 0:
            raise RuntimeError(f"No class scores found in YOLOv6 output {prediction.shape}")
        if self.class_id is None:
            selected_classes = np.argmax(class_scores, axis=1)
        else:
            if self.class_id < 0 or self.class_id >= class_scores.shape[1]:
                raise RuntimeError(
                    f"class_id {self.class_id} is outside model class range 0..{class_scores.shape[1] - 1}"
                )
            selected_classes = np.full(prediction.shape[0], self.class_id, dtype=np.int64)

        scores = objectness * class_scores[np.arange(prediction.shape[0]), selected_classes]
        selected = scores >= self.score_thresh
        boxes = self._xywh_to_xyxy(prediction[selected, :4])
        return boxes, scores[selected].astype(np.float32), selected_classes[selected]

    def _decode_end_to_end_outputs(self, outputs):
        by_name = {name: np.asarray(value) for name, value in zip(self.output_names, outputs)}
        required = {"num_dets", "det_boxes", "det_scores", "det_classes"}
        if not required.issubset(by_name):
            return None

        count = int(np.asarray(by_name["num_dets"]).reshape(-1)[0])
        boxes = by_name["det_boxes"].reshape(-1, 4)[:count].astype(np.float32)
        scores = by_name["det_scores"].reshape(-1)[:count].astype(np.float32)
        classes = by_name["det_classes"].reshape(-1)[:count].astype(np.int64)
        selected = scores >= self.score_thresh
        if self.class_id is not None:
            selected &= classes == self.class_id
        return boxes[selected], scores[selected], classes[selected]

    def detect(self, image):
        blob, meta = self.preprocess(image)
        outputs = self.session.run(None, {self.input_name: blob})

        decoded = self._decode_end_to_end_outputs(outputs)
        if decoded is None:
            if len(outputs) != 1:
                shapes = [np.asarray(output).shape for output in outputs]
                raise RuntimeError(f"Unsupported YOLOv6 outputs: names={self.output_names}, shapes={shapes}")
            boxes, scores, classes = self._decode_raw_output(outputs[0])
            keep = self._nms(boxes, scores, self.nms_thresh)
            boxes, scores, classes = boxes[keep], scores[keep], classes[keep]
        else:
            boxes, scores, classes = decoded

        if scores.size:
            order = scores.argsort()[::-1][: self.max_detections]
            boxes, scores, classes = boxes[order], scores[order], classes[order]

        boxes[:, [0, 2]] = (boxes[:, [0, 2]] - meta["pad_x"]) / meta["scale"]
        boxes[:, [1, 3]] = (boxes[:, [1, 3]] - meta["pad_y"]) / meta["scale"]

        # Keep the detector's full predicted box for HRNet center/scale.  The
        # public detections below remain clipped for drawing/tracking, while an
        # edge face can still use the same square + black-padding semantics as
        # offline landmark inference.
        unclipped_boxes = boxes.copy()
        self.last_unclipped_detections = np.column_stack((unclipped_boxes, scores)).astype(np.float32)
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, meta["original_width"] - 1)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, meta["original_height"] - 1)

        detections = np.column_stack((boxes, scores)).astype(np.float32)
        max_score = float(scores.max()) if scores.size else -1.0
        self._set_debug_info(kept=len(detections), max_score=f"{max_score:.4f}")
        empty_landmarks = np.zeros((len(detections), 0, 2), dtype=np.float32)
        return detections, empty_landmarks
