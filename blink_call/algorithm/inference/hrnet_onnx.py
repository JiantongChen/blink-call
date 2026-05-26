import cv2
import numpy as np

from .utils import create_ort_session


class HRNetONNX:
    """
   HRNet ONNX landmarker for WFLW-98 facial landmarks.

   WFLW-98 98点顺序图 (索引分配):
   ┌─────────────────────────────────────────────────────────────────┐
   │  0 ─── 1 ─── 2 ─── 3 ─── 4 ─── 5 ─── 6 ─── 7 ─── 8 ─── 9     │
   │ 10 ── 11 ── 12 ── 13 ── 14 ── 15 ── 16 ── 17 ── 18 ── 19     │
   │ 20 ── 21 ── 22 ── 23 ── 24 ── 25 ── 26 ── 27 ── 28 ── 29     │
   │                      (面部轮廓 0-31, 共32点)                     │
   │                                                                 │
   │         左眉 30-34          右眉 35-39                         │
   │                                                                 │
   │              眼 60-67          眼 68-75                         │
   │           左眼 8点           右眼 8点                            │
   │                                                                 │
   │                   鼻 76-95 (20点)                              │
   │                                                                 │
   │              嘴 96-97 (2点)                                    │
   └─────────────────────────────────────────────────────────────────┘

   注: 本项目使用 60-67 作为左眼区域, 68-75 作为右眼区域

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
        output_type="auto",
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

        self.session = create_ort_session(self.onnx_path, ctx_id)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [out.name for out in self.session.get_outputs()]

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

        blob = img.transpose(2, 0, 1)[None, ...].astype(np.float32)
        return blob

    @staticmethod
    def _decode_heatmap_to_coords_and_scores(output, input_w, input_h):
        """
        Args:
            output: [1, K, H, W] or [K, H, W]

        Returns:
            coords: [K, 2], crop input coordinate system
            scores: [K]
        """
        if output.ndim == 4:
            output = output[0]

        if output.ndim != 3:
            raise RuntimeError(f"Unexpected heatmap shape: {output.shape}")

        num_joints, hm_h, hm_w = output.shape

        coords = np.zeros((num_joints, 2), dtype=np.float32)
        scores = np.zeros((num_joints,), dtype=np.float32)

        for i in range(num_joints):
            hm = output[i]

            idx = int(np.argmax(hm))
            y, x = np.unravel_index(idx, hm.shape)

            coords[i, 0] = x * (input_w - 1) / max(hm_w - 1, 1)
            coords[i, 1] = y * (input_h - 1) / max(hm_h - 1, 1)
            scores[i] = float(hm[y, x])

        return coords, scores

    def _parse_outputs(self, outputs):
        """
        Parse ONNX outputs automatically.

        Returns:
            coords: [K, 2] in crop input coordinate system
            scores: [K] or None
        """
        input_w, input_h = self.input_size

        heatmap = None
        coords = None
        scores = None

        # Prefer parsing by output name.
        for name, out in zip(self.output_names, outputs):
            lname = name.lower()

            if "heatmap" in lname:
                heatmap = out
            elif "coord" in lname:
                coords = out
            elif "score" in lname or "conf" in lname:
                scores = out

        # Fallback: parse by shape.
        for out in outputs:
            if heatmap is None and out.ndim == 4:
                heatmap = out

            elif coords is None and out.ndim == 3 and out.shape[-1] == 2:
                coords = out

            elif coords is None and out.ndim == 2 and out.shape[-1] == 2:
                coords = out

            elif scores is None and out.ndim == 2 and out.shape[-1] != 2:
                scores = out

            elif scores is None and out.ndim == 1:
                scores = out

        # Case A: coords exists.
        if coords is not None:
            if coords.ndim == 3:
                coords = coords[0]
            elif coords.ndim != 2:
                raise RuntimeError(f"Unexpected coords shape: {coords.shape}")

            coords = coords.astype(np.float32)

            if self.coords_are_normalized:
                coords[:, 0] *= (input_w - 1)
                coords[:, 1] *= (input_h - 1)

            if scores is not None:
                if scores.ndim == 2:
                    scores = scores[0]
                scores = scores.astype(np.float32)

            elif heatmap is not None:
                _, scores = self._decode_heatmap_to_coords_and_scores(
                    heatmap,
                    input_w,
                    input_h,
                )

            return coords, scores

        # Case B: no coords, decode from heatmap.
        if heatmap is not None:
            coords, scores = self._decode_heatmap_to_coords_and_scores(
                heatmap,
                input_w,
                input_h,
            )
            return coords, scores

        # Case C: old one-output coords model.
        if len(outputs) == 1:
            output = outputs[0]

            if output.ndim == 3 and output.shape[-1] == 2:
                coords = output[0].astype(np.float32)
                return coords, None

            if output.ndim == 2 and output.shape[-1] == 2:
                coords = output.astype(np.float32)
                return coords, None

            if output.ndim == 4:
                coords, scores = self._decode_heatmap_to_coords_and_scores(
                    output,
                    input_w,
                    input_h,
                )
                return coords, scores

        shapes = [out.shape for out in outputs]
        raise RuntimeError(f"Unsupported HRNet ONNX output shapes: {shapes}")

    def infer(self, frame, face_bbox_xyxy):
        face_crop, crop_box = self._crop_face(frame, face_bbox_xyxy)

        if face_crop is None:
            return None, None, None

        input_w, input_h = self.input_size

        blob = self._preprocess(face_crop)

        outputs = self.session.run(
            self.output_names,
            {
                self.input_name: blob
            }
        )

        coords, scores = self._parse_outputs(outputs)

        x1, y1, x2, y2 = crop_box

        crop_w = max(1, x2 - x1)
        crop_h = max(1, y2 - y1)

        coords = coords.copy()

        coords[:, 0] = coords[:, 0] * crop_w / max(input_w - 1, 1) + x1
        coords[:, 1] = coords[:, 1] * crop_h / max(input_h - 1, 1) + y1

        coords[:, 0] = np.clip(coords[:, 0], 0, frame.shape[1] - 1)
        coords[:, 1] = np.clip(coords[:, 1], 0, frame.shape[0] - 1)

        return coords.astype(np.float32), crop_box, scores