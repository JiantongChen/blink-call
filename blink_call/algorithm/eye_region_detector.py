import time
from pathlib import Path

import cv2
import numpy as np
import onnxruntime as ort
from PySide6.QtCore import QStandardPaths
from blink_call.utils.head_pose_estimator import InsightFaceHeadPose


APP_MODEL_ROOT = (
    Path(QStandardPaths.writableLocation(QStandardPaths.AppDataLocation))
    / "blink_call"
    / "blink_call_model_files"
)


def _available_providers(ctx_id: int):
    available = ort.get_available_providers()
    if ctx_id >= 0 and "CUDAExecutionProvider" in available:
        return [
            ("CUDAExecutionProvider", {"device_id": ctx_id}),
            "CPUExecutionProvider",
        ]
    return ["CPUExecutionProvider"]


class RetinaFaceONNX:
    """
    RetinaFace ONNX detector.

    Expected outputs:
        stride32: cls, bbox, landmark
        stride16: cls, bbox, landmark
        stride8 : cls, bbox, landmark

    Returns:
        dets: [N, 5] -> x1, y1, x2, y2, score
        landmarks5: [N, 5, 2]
    """

    def __init__(
        self,
        onnx_path,
        input_size=(640, 640),
        ctx_id=0,
        score_thresh=0.8,
        nms_thresh=0.3,
        cls_is_score=True,
    ):
        self.onnx_path = str(onnx_path)
        self.input_size = tuple(input_size)  # (w, h)
        self.score_thresh = float(score_thresh)
        self.nms_thresh = float(nms_thresh)
        self.cls_is_score = bool(cls_is_score)

        self.strides = [32, 16, 8]
        self.anchor_cfg = {
            32: {"SCALES": (32, 16), "BASE_SIZE": 16, "RATIOS": (1.0,)},
            16: {"SCALES": (8, 4), "BASE_SIZE": 16, "RATIOS": (1.0,)},
            8: {"SCALES": (2, 1), "BASE_SIZE": 16, "RATIOS": (1.0,)},
        }

        self.session = ort.InferenceSession(
            self.onnx_path,
            providers=_available_providers(ctx_id),
        )
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [o.name for o in self.session.get_outputs()]

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

        shifts = np.vstack(
            (shift_x.ravel(), shift_y.ravel(), shift_x.ravel(), shift_y.ravel())
        ).transpose().astype(np.float32)

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
        canvas = np.zeros((input_h, input_w, 3), dtype=np.float32)

        pad_x = (input_w - new_w) // 2
        pad_y = (input_h - new_h) // 2
        canvas[pad_y:pad_y + new_h, pad_x:pad_x + new_w] = resized

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
                if "cls" in lname:
                    grouped[(stride, "cls")] = arr
                elif "bbox" in lname:
                    grouped[(stride, "bbox")] = arr
                elif "landmark" in lname:
                    grouped[(stride, "landmark")] = arr

        required = []
        for s in self.strides:
            required.extend([(s, "cls"), (s, "bbox"), (s, "landmark")])

        if all(k in grouped for k in required):
            return grouped

        if len(outputs) != 9:
            raise RuntimeError(f"Expected 9 outputs, got {len(outputs)}")

        grouped = {}
        idx = 0
        for stride in self.strides:
            grouped[(stride, "cls")] = outputs[idx]
            grouped[(stride, "bbox")] = outputs[idx + 1]
            grouped[(stride, "landmark")] = outputs[idx + 2]
            idx += 3

        return grouped

    def decode_one_stride(self, cls, bbox, landmark, stride):
        cls = np.asarray(cls)
        bbox = np.asarray(bbox)
        landmark = np.asarray(landmark)

        if cls.ndim == 3:
            cls = cls[None, ...]
        if bbox.ndim == 3:
            bbox = bbox[None, ...]
        if landmark.ndim == 3:
            landmark = landmark[None, ...]

        _, cls_c, feat_h, feat_w = cls.shape

        cfg = self.anchor_cfg[stride]
        num_anchors = len(cfg["SCALES"]) * len(cfg["RATIOS"])

        if cls_c != 2 * num_anchors:
            raise RuntimeError(
                f"stride {stride}: cls channel error, got {cls_c}, expected {2 * num_anchors}"
            )

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
        scores = cls_prob[:, num_anchors: 2 * num_anchors, :, :]
        scores = scores.transpose(0, 2, 3, 1).reshape(-1)

        bbox = bbox.reshape(1, num_anchors, 4, feat_h, feat_w)
        bbox = bbox.transpose(0, 3, 4, 1, 2).reshape(-1, 4)
        boxes = self.bbox_pred(anchors, bbox)

        landmark = landmark.reshape(1, num_anchors, 10, feat_h, feat_w)
        landmark = landmark.transpose(0, 3, 4, 1, 2).reshape(-1, 5, 2)
        landmarks = self.landmark_pred(anchors, landmark)

        input_w, input_h = self.input_size
        boxes[:, [0, 2]] = np.clip(boxes[:, [0, 2]], 0, input_w - 1)
        boxes[:, [1, 3]] = np.clip(boxes[:, [1, 3]], 0, input_h - 1)
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

        for stride in self.strides:
            boxes, scores, landmarks = self.decode_one_stride(
                cls=grouped[(stride, "cls")],
                bbox=grouped[(stride, "bbox")],
                landmark=grouped[(stride, "landmark")],
                stride=stride,
            )

            keep = np.where(scores >= self.score_thresh)[0]
            if keep.size == 0:
                continue

            all_boxes.append(boxes[keep])
            all_scores.append(scores[keep])
            all_landmarks.append(landmarks[keep])

        if len(all_boxes) == 0:
            return (
                np.zeros((0, 5), dtype=np.float32),
                np.zeros((0, 5, 2), dtype=np.float32),
            )

        boxes = np.vstack(all_boxes)
        scores = np.concatenate(all_scores)
        landmarks = np.vstack(all_landmarks)

        dets = np.hstack([boxes, scores[:, None]]).astype(np.float32)
        keep = self.nms(dets, self.nms_thresh)
        dets = dets[keep]
        landmarks = landmarks[keep]

        scale = meta["scale"]
        pad_x = meta["pad_x"]
        pad_y = meta["pad_y"]

        dets[:, [0, 2]] = (dets[:, [0, 2]] - pad_x) / scale
        dets[:, [1, 3]] = (dets[:, [1, 3]] - pad_y) / scale

        landmarks[:, :, 0] = (landmarks[:, :, 0] - pad_x) / scale
        landmarks[:, :, 1] = (landmarks[:, :, 1] - pad_y) / scale

        dets[:, [0, 2]] = np.clip(dets[:, [0, 2]], 0, original_w - 1)
        dets[:, [1, 3]] = np.clip(dets[:, [1, 3]], 0, original_h - 1)
        landmarks[:, :, 0] = np.clip(landmarks[:, :, 0], 0, original_w - 1)
        landmarks[:, :, 1] = np.clip(landmarks[:, :, 1], 0, original_h - 1)

        return dets.astype(np.float32), landmarks.astype(np.float32)


class HRNetONNX:
    """
    HRNet ONNX landmarker for WFLW-98 facial landmarks.

    Supported outputs:
        coords : [1, K, 2] or [K, 2]
        heatmap: [1, K, H, W]

    Returned landmarks are mapped back to ORIGINAL image coordinates.
    """

    def __init__(
        self,
        onnx_path,
        input_size=(256, 256),
        ctx_id=0,
        output_type="coords",
        norm_type="imagenet",
        coords_are_normalized=False,
        face_expand_ratio=1.25,
    ):
        self.onnx_path = str(onnx_path)
        self.input_size = tuple(input_size)  # (w, h)
        self.output_type = output_type
        self.norm_type = norm_type
        self.coords_are_normalized = bool(coords_are_normalized)
        self.face_expand_ratio = float(face_expand_ratio)

        self.session = ort.InferenceSession(
            self.onnx_path,
            providers=_available_providers(ctx_id),
        )
        self.input_name = self.session.get_inputs()[0].name

    def _crop_face(self, frame, face_bbox_xyxy):
        h, w = frame.shape[:2]
        x1, y1, x2, y2 = map(float, face_bbox_xyxy)

        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)
        bw = x2 - x1
        bh = y2 - y1
        side = max(bw, bh) * self.face_expand_ratio

        nx1 = max(0, int(round(cx - 0.5 * side)))
        ny1 = max(0, int(round(cy - 0.5 * side)))
        nx2 = min(w, int(round(cx + 0.5 * side)))
        ny2 = min(h, int(round(cy + 0.5 * side)))

        if nx2 - nx1 < 2 or ny2 - ny1 < 2:
            return None, None

        crop = frame[ny1:ny2, nx1:nx2]
        if crop.size == 0:
            return None, None
        return crop, (nx1, ny1, nx2, ny2)

    def _preprocess(self, face_crop):
        input_w, input_h = self.input_size
        img = cv2.resize(face_crop, (input_w, input_h))
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0

        if self.norm_type == "imagenet":
            mean = np.array([0.485, 0.456, 0.406], dtype=np.float32)
            std = np.array([0.229, 0.224, 0.225], dtype=np.float32)
            img = (img - mean) / std

        return img.transpose(2, 0, 1)[None, ...].astype(np.float32)

    @staticmethod
    def _decode_heatmap_to_coords(output, input_w, input_h):
        if output.ndim == 4:
            output = output[0]

        num_joints, hm_h, hm_w = output.shape
        coords = np.zeros((num_joints, 2), dtype=np.float32)
        for i in range(num_joints):
            hm = output[i]
            idx = np.argmax(hm)
            y, x = np.unravel_index(idx, hm.shape)
            coords[i, 0] = x * (input_w - 1) / max(hm_w - 1, 1)
            coords[i, 1] = y * (input_h - 1) / max(hm_h - 1, 1)
        return coords

    def infer(self, frame, face_bbox_xyxy):
        face_crop, crop_box = self._crop_face(frame, face_bbox_xyxy)
        if face_crop is None:
            return None, None

        input_w, input_h = self.input_size
        blob = self._preprocess(face_crop)
        output = self.session.run(None, {self.input_name: blob})[0]

        if self.output_type == "coords":
            if output.ndim == 3:
                coords = output[0]
            elif output.ndim == 2:
                coords = output
            else:
                raise RuntimeError(f"Unexpected coords output shape: {output.shape}")
            coords = coords.astype(np.float32)
            if self.coords_are_normalized:
                coords[:, 0] *= (input_w - 1)
                coords[:, 1] *= (input_h - 1)
        elif self.output_type == "heatmap":
            coords = self._decode_heatmap_to_coords(output, input_w, input_h)
        else:
            raise ValueError(f"Unsupported output_type: {self.output_type}")

        x1, y1, x2, y2 = crop_box
        crop_w = max(1, x2 - x1)
        crop_h = max(1, y2 - y1)

        coords = coords.copy()
        coords[:, 0] = coords[:, 0] * crop_w / max(input_w - 1, 1) + x1
        coords[:, 1] = coords[:, 1] * crop_h / max(input_h - 1, 1) + y1
        coords[:, 0] = np.clip(coords[:, 0], 0, frame.shape[1] - 1)
        coords[:, 1] = np.clip(coords[:, 1], 0, frame.shape[0] - 1)
        return coords.astype(np.float32), crop_box


class EyeRegionDetector:
    """
    Two-stage eye-region detector:
        1. local RetinaFace ONNX for face detection
        2. local HRNet ONNX for landmark detection

    Eye selection rule:
        Same as the original InsightFace-only version:
            yaw > 0  -> left eye
            yaw <= 0 -> right eye
    """

    def __init__(self, configs):
        self.ctx_id = int(configs.get("ctx_id", -1))
        self.det_size = tuple(configs.get("det_size", (640, 640)))
        self.det_thresh = float(configs.get("det_thresh", 0.8))
        self.det_nms_thresh = float(configs.get("det_nms_thresh", 0.3))
        self.eye_padding = int(configs.get("eye_padding", 20))
        self.max_num_faces = int(configs.get("max_num_faces", 1))

        default_retina_path = APP_MODEL_ROOT / "retinaface" / "retinaface.onnx"
        default_hrnet_path = APP_MODEL_ROOT / "hrnet" / "hrnet_wflw_98_coords.onnx"

        self.retina_onnx_path = str(configs.get("retina_onnx_path", default_retina_path))
        self.hrnet_onnx_path = str(configs.get("hrnet_onnx_path", default_hrnet_path))

        self.retina_cls_is_score = bool(configs.get("retina_cls_is_score", True))

        self.hrnet_input_size = tuple(configs.get("hrnet_input_size", (256, 256)))
        self.hrnet_output_type = str(configs.get("hrnet_output_type", "coords"))
        self.hrnet_norm_type = str(configs.get("hrnet_norm_type", "imagenet"))
        self.hrnet_coords_are_normalized = bool(
            configs.get("hrnet_coords_are_normalized", False)
        )
        self.face_expand_ratio = float(configs.get("face_expand_ratio", 1.25))

        self.face_detector = RetinaFaceONNX(
            onnx_path=self.retina_onnx_path,
            input_size=self.det_size,
            ctx_id=self.ctx_id,
            score_thresh=self.det_thresh,
            nms_thresh=self.det_nms_thresh,
            cls_is_score=self.retina_cls_is_score,
        )

        self.landmarker = HRNetONNX(
            onnx_path=self.hrnet_onnx_path,
            input_size=self.hrnet_input_size,
            ctx_id=self.ctx_id,
            output_type=self.hrnet_output_type,
            norm_type=self.hrnet_norm_type,
            coords_are_normalized=self.hrnet_coords_are_normalized,
            face_expand_ratio=self.face_expand_ratio,
        )

        self.eye_indices = configs.get(
            "eye_indices",
            {
                "left": list(range(60, 68)),
                "right": list(range(68, 76)),
            },
        )

        self.head_pose_estimator = InsightFaceHeadPose()

        self._last_good_eye_bbox = None
        self._last_good_face_bbox = None
        self._last_good_landmarks = None

    def _select_eye(self, landmarks, frame_shape):
        head_pose = self.head_pose_estimator.estimate(landmarks, frame_shape)
        selected_eye = "right" if head_pose["yaw"] > 0 else "left"
        return selected_eye, head_pose

    def _points_to_bbox_local(self, points, padding=None):
        if padding is None:
            padding = self.eye_padding
        x_min = int(np.floor(np.min(points[:, 0]))) - padding
        y_min = int(np.floor(np.min(points[:, 1]))) - padding
        x_max = int(np.ceil(np.max(points[:, 0]))) + padding
        y_max = int(np.ceil(np.max(points[:, 1]))) + padding
        return [x_min, y_min, x_max, y_max]

    def _safe_points_to_bbox(self, points, frame_shape, padding=None):
        if padding is None:
            padding = self.eye_padding
        bbox = self._points_to_bbox_local(points, padding=padding)
        h, w = frame_shape[:2]
        bbox[0] = max(0, min(w - 1, bbox[0]))
        bbox[1] = max(0, min(h - 1, bbox[1]))
        bbox[2] = max(0, min(w - 1, bbox[2]))
        bbox[3] = max(0, min(h - 1, bbox[3]))
        return bbox

    @staticmethod
    def _fallback_bbox_from_frame(frame):
        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 3
        bw, bh = max(40, w // 5), max(25, h // 10)
        return [cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2]

    def _cache_success(self, eye_bbox, face_bbox, landmarks):
        self._last_good_eye_bbox = [int(v) for v in eye_bbox]
        self._last_good_face_bbox = [float(v) for v in face_bbox]
        self._last_good_landmarks = (
            landmarks.tolist() if isinstance(landmarks, np.ndarray) else landmarks
        )

    def _fallback_result(self, frame, debug_info):
        if self._last_good_eye_bbox is not None:
            return self._return_data(
                eye_bbox_xyxy=self._last_good_eye_bbox,
                face_bbox_xyxy=self._last_good_face_bbox,
                landmarks=self._last_good_landmarks,
                debug_info=f"{debug_info}, using_last_good_bbox=true",
            )

        fallback = self._fallback_bbox_from_frame(frame)
        return self._return_data(
            eye_bbox_xyxy=fallback,
            face_bbox_xyxy=None,
            landmarks=None,
            debug_info=f"{debug_info}, using_center_fallback_bbox=true",
        )

    def detect(self, frame):
        if frame is None:
            return self._return_data(debug_info="frame is None")

        if not isinstance(frame, np.ndarray) or frame.ndim < 2:
            return self._return_data(debug_info="invalid frame data")

        t0 = time.perf_counter()
        try:
            faces, landmarks5 = self.face_detector.detect(frame)
        except Exception as exc:
            return self._fallback_result(frame, f"retinaface onnx inference error: {exc}")

        if faces.shape[0] == 0:
            return self._fallback_result(frame, "no face detected")

        if faces.shape[0] > 1:
            areas = (faces[:, 2] - faces[:, 0]) * (faces[:, 3] - faces[:, 1])
            face_idx = int(np.argmax(areas))
        else:
            face_idx = 0

        face = faces[face_idx]
        face_bbox = face[:4].tolist()
        t1 = time.perf_counter()

        try:
            landmarks, crop_box = self.landmarker.infer(frame, face_bbox)
        except Exception as exc:
            return self._fallback_result(frame, f"hrnet onnx inference error: {exc}")

        if landmarks is None or landmarks.ndim != 2 or landmarks.shape[1] != 2:
            bad_shape = None if landmarks is None else landmarks.shape
            return self._fallback_result(frame, f"invalid landmarks predicted: {bad_shape}")

        try:
            left_eye_points = landmarks[self.eye_indices["left"]]
            right_eye_points = landmarks[self.eye_indices["right"]]
        except Exception as exc:
            return self._fallback_result(frame, f"eye index error: {exc}")

        try:
            selected_eye, head_pose = self._select_eye(landmarks, frame.shape)
        except Exception as exc:
            return self._fallback_result(frame, f"head pose estimation error: {exc}")

        selected_points = left_eye_points if selected_eye == "left" else right_eye_points
        eye_bbox = self._safe_points_to_bbox(
            selected_points, frame.shape, padding=self.eye_padding
        )
        t2 = time.perf_counter()

        self._cache_success(eye_bbox, face_bbox, landmarks)

        debug_info = (
            f"select {selected_eye} eye: "
            f"det_ms={(t1 - t0) * 1000.0:.1f}, "
            f"lmk_ms={(t2 - t1) * 1000.0:.1f}, "
            f"total_ms={(t2 - t0) * 1000.0:.1f}, "
            f"yaw:{head_pose['yaw']:.3f}, "
            f"pitch:{head_pose['pitch']:.3f}, "
            f"roll:{head_pose['roll']:.3f}"
        )
        if crop_box is not None:
            debug_info += f", crop_box={list(map(int, crop_box))}"

        return self._return_data(
            eye_bbox_xyxy=eye_bbox,
            face_bbox_xyxy=[float(v) for v in face_bbox],
            landmarks=landmarks.tolist(),
            debug_info=debug_info,
        )

    def _return_data(
        self,
        eye_bbox_xyxy=None,
        face_bbox_xyxy=None,
        landmarks=None,
        debug_info="",
    ):
        return {
            "timestamp_ms": int(time.time() * 1000),
            "eye_bbox_xyxy": eye_bbox_xyxy,
            "face_bbox_xyxy": face_bbox_xyxy,
            "landmarks": landmarks,
            "debug_info": debug_info,
        }