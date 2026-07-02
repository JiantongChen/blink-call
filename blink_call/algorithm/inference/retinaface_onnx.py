import cv2
import numpy as np

from blink_call.utils.helper import Helper


class RetinaFaceONNX:
    """
    RetinaFace ONNX detector.

    Supported outputs:
        6-output bbox-only model:
            stride32: cls, bbox
            stride16: cls, bbox
            stride8 : cls, bbox
        9-output landmark model:
            stride32: cls, bbox, landmark
            stride16: cls, bbox, landmark
            stride8 : cls, bbox, landmark

    Returns:
        dets: [N, 5] -> x1, y1, x2, y2, score
        landmarks5: [N, 5, 2] when model has landmarks, otherwise [N, 0, 2]
    """

    def __init__(
        self,
        onnx_path,
        input_size=(640, 640),
        ctx_id=0,
        score_thresh=0.8,
        nms_thresh=0.3,
        cls_is_score=True,
        bgr_to_rgb=True,
    ):
        self.onnx_path = str(onnx_path)
        self.input_size = tuple(input_size)  # (w, h)
        self.score_thresh = float(score_thresh)
        self.nms_thresh = float(nms_thresh)
        self.cls_is_score = bool(cls_is_score)
        self.bgr_to_rgb = bool(bgr_to_rgb)
        self.last_debug_info = ""

        self.strides = [32, 16, 8]
        self.anchor_cfg = {
            32: {"SCALES": (32, 16), "BASE_SIZE": 16, "RATIOS": (1.0,)},
            16: {"SCALES": (8, 4), "BASE_SIZE": 16, "RATIOS": (1.0,)},
            8: {"SCALES": (2, 1), "BASE_SIZE": 16, "RATIOS": (1.0,)},
        }

        self.session = Helper.create_ort_session(self.onnx_path, ctx_id)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]
        self._use_static_model_size_if_available()
        self.last_debug_info = (
            f"retina_path={self.onnx_path}, input_size={self.input_size}, "
            f"outputs={len(self.output_names)}, bgr_to_rgb={self.bgr_to_rgb}, "
            f"cls_is_score={self.cls_is_score}, score_thresh={self.score_thresh}"
        )

    def _use_static_model_size_if_available(self):
        shape = self.session.get_inputs()[0].shape
        if len(shape) != 4:
            return
        h = shape[2]
        w = shape[3]
        if isinstance(h, int) and isinstance(w, int):
            self.input_size = (w, h)

    @staticmethod
    def softmax_channel(cls_score, num_anchors):
        n, c, h, w = cls_score.shape
        cls_reshape = cls_score.reshape((n, 2, -1, w))
        cls_reshape = cls_reshape - np.max(cls_reshape, axis=1, keepdims=True)
        cls_exp = np.exp(cls_reshape)
        cls_prob = cls_exp / np.sum(cls_exp, axis=1, keepdims=True)
        cls_prob = cls_prob.reshape((n, 2 * num_anchors, h, w))
        return cls_prob

    @staticmethod
    def generate_base_anchors(base_size=16, ratios=(1.0,), scales=(1.0,)):
        base_anchor = np.array([0, 0, base_size - 1, base_size - 1], dtype=np.float32)

        x1, y1, x2, y2 = base_anchor
        w = x2 - x1 + 1
        h = y2 - y1 + 1
        x_ctr = x1 + 0.5 * (w - 1)
        y_ctr = y1 + 0.5 * (h - 1)
        size = w * h

        anchors = []
        for ratio in ratios:
            size_ratio = size / ratio
            ws = np.round(np.sqrt(size_ratio))
            hs = np.round(ws * ratio)
            for scale in scales:
                ww = ws * scale
                hh = hs * scale
                anchor = [
                    x_ctr - 0.5 * (ww - 1),
                    y_ctr - 0.5 * (hh - 1),
                    x_ctr + 0.5 * (ww - 1),
                    y_ctr + 0.5 * (hh - 1),
                ]
                anchors.append(anchor)
        return np.array(anchors, dtype=np.float32)

    @staticmethod
    def generate_anchors_plane(feat_h, feat_w, stride, base_anchors):
        shift_x = np.arange(0, feat_w) * stride
        shift_y = np.arange(0, feat_h) * stride
        shift_x, shift_y = np.meshgrid(shift_x, shift_y)

        shifts = (
            np.vstack((shift_x.ravel(), shift_y.ravel(), shift_x.ravel(), shift_y.ravel()))
            .transpose()
            .astype(np.float32)
        )

        a = base_anchors.shape[0]
        k = shifts.shape[0]

        anchors = base_anchors.reshape((1, a, 4)) + shifts.reshape((k, 1, 4))
        return anchors.reshape((k * a, 4)).astype(np.float32)

    @staticmethod
    def bbox_pred(anchors, bbox_deltas):
        widths = anchors[:, 2] - anchors[:, 0] + 1.0
        heights = anchors[:, 3] - anchors[:, 1] + 1.0
        ctr_x = anchors[:, 0] + 0.5 * (widths - 1.0)
        ctr_y = anchors[:, 1] + 0.5 * (heights - 1.0)

        dx = bbox_deltas[:, 0]
        dy = bbox_deltas[:, 1]
        dw = bbox_deltas[:, 2]
        dh = bbox_deltas[:, 3]

        pred_ctr_x = dx * widths + ctr_x
        pred_ctr_y = dy * heights + ctr_y
        pred_w = np.exp(dw) * widths
        pred_h = np.exp(dh) * heights

        pred_boxes = np.zeros_like(bbox_deltas, dtype=np.float32)
        pred_boxes[:, 0] = pred_ctr_x - 0.5 * (pred_w - 1.0)
        pred_boxes[:, 1] = pred_ctr_y - 0.5 * (pred_h - 1.0)
        pred_boxes[:, 2] = pred_ctr_x + 0.5 * (pred_w - 1.0)
        pred_boxes[:, 3] = pred_ctr_y + 0.5 * (pred_h - 1.0)
        return pred_boxes

    @staticmethod
    def landmark_pred(anchors, landmark_deltas):
        widths = anchors[:, 2] - anchors[:, 0] + 1.0
        heights = anchors[:, 3] - anchors[:, 1] + 1.0
        ctr_x = anchors[:, 0] + 0.5 * (widths - 1.0)
        ctr_y = anchors[:, 1] + 0.5 * (heights - 1.0)

        pred = np.zeros_like(landmark_deltas, dtype=np.float32)
        for i in range(5):
            pred[:, i, 0] = landmark_deltas[:, i, 0] * widths + ctr_x
            pred[:, i, 1] = landmark_deltas[:, i, 1] * heights + ctr_y
        return pred

    @staticmethod
    def nms(dets, thresh):
        if dets.shape[0] == 0:
            return []

        x1 = dets[:, 0]
        y1 = dets[:, 1]
        x2 = dets[:, 2]
        y2 = dets[:, 3]
        scores = dets[:, 4]

        areas = np.maximum(0.0, x2 - x1 + 1.0) * np.maximum(0.0, y2 - y1 + 1.0)
        order = scores.argsort()[::-1]
        keep = []

        while order.size > 0:
            i = order[0]
            keep.append(int(i))

            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1.0)
            h = np.maximum(0.0, yy2 - yy1 + 1.0)
            inter = w * h
            iou = inter / np.maximum(areas[i] + areas[order[1:]] - inter, 1e-6)

            inds = np.where(iou <= thresh)[0]
            order = order[inds + 1]

        return keep

    def preprocess(self, img):
        """
        Keep aspect ratio + pad to input_size.
        """
        input_w, input_h = self.input_size
        orig_h, orig_w = img.shape[:2]

        scale = min(input_w / float(orig_w), input_h / float(orig_h))
        new_w = int(round(orig_w * scale))
        new_h = int(round(orig_h * scale))

        resized = cv2.resize(img, (new_w, new_h)).astype(np.float32)
        if self.bgr_to_rgb:
            resized = resized[:, :, ::-1]
        canvas = np.zeros((input_h, input_w, 3), dtype=np.float32)

        pad_x = (input_w - new_w) // 2
        pad_y = (input_h - new_h) // 2
        canvas[pad_y : pad_y + new_h, pad_x : pad_x + new_w] = resized

        blob = canvas.transpose(2, 0, 1)[None, :, :, :].astype(np.float32)
        meta = {
            "scale": scale,
            "pad_x": pad_x,
            "pad_y": pad_y,
            "orig_w": orig_w,
            "orig_h": orig_h,
        }
        return blob, meta

    def group_outputs(self, outputs):
        grouped = {}

        for name, arr in zip(self.output_names, outputs):
            lname = name.lower()
            for stride in self.strides:
                if f"stride{stride}" not in lname:
                    continue
                if "landmark" in lname:
                    grouped[(stride, "landmark")] = arr
                elif "bbox" in lname:
                    grouped[(stride, "bbox")] = arr
                elif "cls" in lname:
                    grouped[(stride, "cls")] = arr

        required_box = []
        for s in self.strides:
            required_box.extend([(s, "cls"), (s, "bbox")])

        if all(k in grouped for k in required_box):
            return grouped

        if len(outputs) not in (6, 9):
            raise RuntimeError(f"Expected 6 or 9 outputs, got {len(outputs)}")

        grouped = {}
        idx = 0
        has_landmark = len(outputs) == 9
        for stride in self.strides:
            grouped[(stride, "cls")] = outputs[idx]
            grouped[(stride, "bbox")] = outputs[idx + 1]
            idx += 2
            if has_landmark:
                grouped[(stride, "landmark")] = outputs[idx]
                idx += 1

        return grouped

    def decode_one_stride(self, cls, bbox, landmark, stride):
        cls = np.asarray(cls)
        bbox = np.asarray(bbox)
        if landmark is not None:
            landmark = np.asarray(landmark)

        if cls.ndim == 3:
            cls = cls[None, ...]
        if bbox.ndim == 3:
            bbox = bbox[None, ...]
        if landmark is not None and landmark.ndim == 3:
            landmark = landmark[None, ...]

        _, cls_c, feat_h, feat_w = cls.shape

        cfg = self.anchor_cfg[stride]
        num_anchors = len(cfg["SCALES"]) * len(cfg["RATIOS"])

        if cls_c != 2 * num_anchors:
            raise RuntimeError(f"stride {stride}: cls channel error, got {cls_c}, expected {2 * num_anchors}")

        base_anchors = self.generate_base_anchors(
            base_size=cfg["BASE_SIZE"],
            ratios=cfg["RATIOS"],
            scales=cfg["SCALES"],
        )
        anchors = self.generate_anchors_plane(
            feat_h=feat_h,
            feat_w=feat_w,
            stride=stride,
            base_anchors=base_anchors,
        )

        cls_prob = self.softmax_channel(cls, num_anchors) if self.cls_is_score else cls
        scores = cls_prob[:, num_anchors : 2 * num_anchors, :, :]
        scores = scores.transpose(0, 2, 3, 1).reshape(-1)

        bbox = bbox.reshape(1, num_anchors, 4, feat_h, feat_w)
        bbox = bbox.transpose(0, 3, 4, 1, 2).reshape(-1, 4)
        boxes = self.bbox_pred(anchors, bbox)

        landmarks = None
        if landmark is not None:
            landmark = landmark.reshape(1, num_anchors, 10, feat_h, feat_w)
            landmark = landmark.transpose(0, 3, 4, 1, 2).reshape(-1, 5, 2)
            landmarks = self.landmark_pred(anchors, landmark)

        input_w, input_h = self.input_size
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, input_w - 1)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, input_h - 1)
        if landmarks is not None:
            landmarks[:, :, 0] = np.clip(landmarks[:, :, 0], 0, input_w - 1)
            landmarks[:, :, 1] = np.clip(landmarks[:, :, 1], 0, input_h - 1)

        return boxes, scores, landmarks

    def detect(self, img):
        original_h, original_w = img.shape[:2]

        blob, meta = self.preprocess(img)
        outputs = self.session.run(None, {self.input_name: blob})
        grouped = self.group_outputs(outputs)

        all_boxes = []
        all_scores = []
        all_landmarks = []
        max_score_seen = -1.0
        has_landmark = all((stride, "landmark") in grouped for stride in self.strides)

        for stride in self.strides:
            boxes, scores, landmarks = self.decode_one_stride(
                cls=grouped[(stride, "cls")],
                bbox=grouped[(stride, "bbox")],
                landmark=grouped.get((stride, "landmark")),
                stride=stride,
            )

            if scores.size:
                max_score_seen = max(max_score_seen, float(np.max(scores)))

            keep = np.where(scores >= self.score_thresh)[0]
            if keep.size == 0:
                continue

            all_boxes.append(boxes[keep])
            all_scores.append(scores[keep])
            if has_landmark and landmarks is not None:
                all_landmarks.append(landmarks[keep])

        if len(all_boxes) == 0:
            self.last_debug_info = (
                f"retina_path={self.onnx_path}, input_size={self.input_size}, "
                f"outputs={len(outputs)}, has_landmark={has_landmark}, "
                f"max_score={max_score_seen:.4f}, score_thresh={self.score_thresh}, "
                f"bgr_to_rgb={self.bgr_to_rgb}, cls_is_score={self.cls_is_score}"
            )
            return (
                np.zeros((0, 5), dtype=np.float32),
                np.zeros((0, 0, 2), dtype=np.float32),
            )

        boxes = np.vstack(all_boxes)
        scores = np.concatenate(all_scores)
        landmarks = np.vstack(all_landmarks) if has_landmark else None

        dets = np.hstack([boxes, scores[:, None]]).astype(np.float32)
        keep = self.nms(dets, self.nms_thresh)
        dets = dets[keep]
        if landmarks is not None:
            landmarks = landmarks[keep]

        scale = meta["scale"]
        pad_x = meta["pad_x"]
        pad_y = meta["pad_y"]

        dets[:, [0, 2]] = (dets[:, [0, 2]] - pad_x) / scale
        dets[:, [1, 3]] = (dets[:, [1, 3]] - pad_y) / scale

        if landmarks is not None:
            landmarks[:, :, 0] = (landmarks[:, :, 0] - pad_x) / scale
            landmarks[:, :, 1] = (landmarks[:, :, 1] - pad_y) / scale

        dets[:, [0, 2]] = np.clip(dets[:, [0, 2]], 0, original_w - 1)
        dets[:, [1, 3]] = np.clip(dets[:, [1, 3]], 0, original_h - 1)
        if landmarks is not None:
            landmarks[:, :, 0] = np.clip(landmarks[:, :, 0], 0, original_w - 1)
            landmarks[:, :, 1] = np.clip(landmarks[:, :, 1], 0, original_h - 1)
        else:
            landmarks = np.zeros((dets.shape[0], 0, 2), dtype=np.float32)

        self.last_debug_info = (
            f"retina_path={self.onnx_path}, input_size={self.input_size}, "
            f"outputs={len(outputs)}, has_landmark={has_landmark}, "
            f"max_score={max_score_seen:.4f}, kept={dets.shape[0]}, "
            f"score_thresh={self.score_thresh}, bgr_to_rgb={self.bgr_to_rgb}, "
            f"cls_is_score={self.cls_is_score}"
        )
        return dets.astype(np.float32), landmarks.astype(np.float32)
