import time


class EyeRegionDetector:
    """
    Placeholder interface for eye-region detection model.
    Replace `detect` implementation with real model inference.
    """

    def __init__(self, configs):
        pass

    def detect(self, frame):
        if frame is None:
            return {"timestamp_ms": int(time.time() * 1000), "bbox_xyxy": None, "debug_info": "no_frame"}

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 3
        bw, bh = max(40, w // 5), max(25, h // 10)
        bbox = [cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2]
        time.sleep(3)

        return {
            "timestamp_ms": int(time.time() * 1000),
            "bbox_xyxy": bbox,
            "debug_info": "eye_bbox_placeholder",
        }
