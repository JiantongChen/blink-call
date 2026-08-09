import cv2
import numpy as np

from blink_call.utils.helper import Helper


class HRNetONNX:
    """
    HRNet ONNX landmarker for WFLW-98 facial landmarks.
    WFLW: https://wywu.github.io/projects/LAB/WFLW.html

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

        self.session = Helper.create_ort_session(self.onnx_path, ctx_id)
        self.input_name = self.session.get_inputs()[0].name
        self.output_names = [out.name for out in self.session.get_outputs()]

    def _crop_face(self, frame, face_bbox_xyxy):
        h, w = frame.shape[:2]

        x1, y1, x2, y2 = map(float, face_bbox_xyxy)

        cx = 0.5 * (x1 + x2)
        cy = 0.5 * (y1 + y2)

        bw = x2 - x1
        bh = y2 - y1

        side = max(2, int(round(max(bw, bh) * self.face_expand_ratio)))
        nx1 = int(round(cx - 0.5 * side))
        ny1 = int(round(cy - 0.5 * side))
        nx2 = nx1 + side
        ny2 = ny1 + side

        # Keep the complete center/scale square, just like the original HRNet
        # crop.  Areas outside the camera frame are padded with black instead
        # of clipping the crop and stretching a non-square image to 256x256.
        src_x1 = max(0, nx1)
        src_y1 = max(0, ny1)
        src_x2 = min(w, nx2)
        src_y2 = min(h, ny2)
        if src_x2 - src_x1 < 2 or src_y2 - src_y1 < 2:
            return None, None

        crop = np.zeros((side, side, frame.shape[2]), dtype=frame.dtype)
        dst_x1 = src_x1 - nx1
        dst_y1 = src_y1 - ny1
        dst_x2 = dst_x1 + (src_x2 - src_x1)
        dst_y2 = dst_y1 + (src_y2 - src_y1)
        crop[dst_y1:dst_y2, dst_x1:dst_x2] = frame[src_y1:src_y2, src_x1:src_x2]

        return crop, {
            "center": np.array([cx, cy], dtype=np.float32),
            "scale": float(side) / 200.0,
            "virtual_box": (nx1, ny1, nx2, ny2),
        }

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
    def _decode_heatmap_to_coords_and_scores(output):
        """
        Args:
            output: [1, K, H, W] or [K, H, W]

        Returns:
            coords: [K, 2], one-based heatmap coordinate system
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
            scores[i] = float(hm[y, x])

            # Match the WFLW HRNet decode_preds implementation: convert the
            # argmax to one-based coordinates, refine it using the local
            # heatmap gradient, then apply its half-pixel offset.
            px = float(x + 1)
            py = float(y + 1)
            if 1 < px < hm_w and 1 < py < hm_h:
                diff_x = hm[y, x + 1] - hm[y, x - 1]
                diff_y = hm[y + 1, x] - hm[y - 1, x]
                px += float(np.sign(diff_x)) * 0.25
                py += float(np.sign(diff_y)) * 0.25

            coords[i, 0] = px + 0.5
            coords[i, 1] = py + 0.5

        return coords, scores, (hm_w, hm_h)

    @staticmethod
    def _get_transform(center, scale, output_size):
        """Build the affine transform used by the original HRNet crop."""
        output_w, output_h = output_size
        source_size = 200.0 * float(scale)
        transform = np.eye(3, dtype=np.float32)
        transform[0, 0] = output_w / source_size
        transform[1, 1] = output_h / source_size
        transform[0, 2] = output_w * (-float(center[0]) / source_size + 0.5)
        transform[1, 2] = output_h * (-float(center[1]) / source_size + 0.5)
        return transform

    @classmethod
    def _transform_preds_to_image(cls, coords, center, scale, output_size):
        """Apply HRNet's one-based inverse center/scale transformation."""
        inverse = np.linalg.inv(cls._get_transform(center, scale, output_size))
        transformed = np.empty_like(coords, dtype=np.float32)
        for index, point in enumerate(coords):
            source = np.array([point[0] - 1.0, point[1] - 1.0, 1.0], dtype=np.float32)
            mapped = inverse @ source
            transformed[index] = mapped[:2] + 1.0
        return transformed

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

        # Prefer heatmaps so online decoding follows the PyTorch
        # decode_preds path, including quarter-pixel refinement.
        if heatmap is not None:
            decoded, decoded_scores, heatmap_size = self._decode_heatmap_to_coords_and_scores(heatmap)
            return decoded, decoded_scores, ("heatmap", heatmap_size)

        # Fall back to coordinate-only exports for compatibility.
        if coords is not None:
            if coords.ndim == 3:
                coords = coords[0]
            elif coords.ndim != 2:
                raise RuntimeError(f"Unexpected coords shape: {coords.shape}")

            coords = coords.astype(np.float32)

            if self.coords_are_normalized:
                coords[:, 0] *= input_w - 1
                coords[:, 1] *= input_h - 1

            if scores is not None:
                if scores.ndim == 2:
                    scores = scores[0]
                scores = scores.astype(np.float32)

            return coords, scores, ("input", self.input_size)

        # Old one-output coordinate model.
        if len(outputs) == 1:
            output = outputs[0]

            if output.ndim == 3 and output.shape[-1] == 2:
                coords = output[0].astype(np.float32)
                return coords, None, ("input", self.input_size)

            if output.ndim == 2 and output.shape[-1] == 2:
                coords = output.astype(np.float32)
                return coords, None, ("input", self.input_size)

            if output.ndim == 4:
                coords, scores, heatmap_size = self._decode_heatmap_to_coords_and_scores(output)
                return coords, scores, ("heatmap", heatmap_size)

        shapes = [out.shape for out in outputs]
        raise RuntimeError(f"Unsupported HRNet ONNX output shapes: {shapes}")

    def infer(self, frame, face_bbox_xyxy):
        face_crop, crop_info = self._crop_face(frame, face_bbox_xyxy)

        if face_crop is None:
            return None, None, None

        input_w, input_h = self.input_size

        blob = self._preprocess(face_crop)

        outputs = self.session.run(self.output_names, {self.input_name: blob})

        coords, scores, coordinate_info = self._parse_outputs(outputs)
        coordinate_space, coordinate_size = coordinate_info

        if coordinate_space == "heatmap":
            coords = self._transform_preds_to_image(
                coords,
                crop_info["center"],
                crop_info["scale"],
                coordinate_size,
            )
        else:
            # Coordinate-only exports use the resized 256x256 crop space.
            x1, y1, x2, y2 = crop_info["virtual_box"]
            crop_w = max(1, x2 - x1)
            crop_h = max(1, y2 - y1)
            coords = coords.copy()
            coords[:, 0] = coords[:, 0] * crop_w / max(input_w - 1, 1) + x1
            coords[:, 1] = coords[:, 1] * crop_h / max(input_h - 1, 1) + y1

        # Do not clip landmarks here: the offline decode path also preserves
        # points outside the image.  Downstream bbox generation clamps the
        # final crop to valid image bounds.
        return coords.astype(np.float32), crop_info["virtual_box"], scores
