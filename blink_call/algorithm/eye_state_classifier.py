import time


class EyeStateClassifier:
    """
    Placeholder interface for eye-state (open/closed) classification model.
    Replace `classify` implementation with real model inference.
    """

    def __init__(self, configs):
        self.test_state_list = [1] * 10 + [0] * 10 + [1] * 20
        self.idx = 0

    def classify(self, eye_roi):
        if eye_roi is None:
            return {"timestamp_ms": int(time.time() * 1000), "state": "unknown", "debug_info": "no_eye_roi"}

        state = "open" if (self.test_state_list[self.idx] == 1) else "closed"

        self.idx += 1
        if self.idx >= len(self.test_state_list):
            self.idx = 0

        time.sleep(0.1)

        return {
            "timestamp_ms": int(time.time() * 1000),
            "state": state,
            "debug_info": state,
        }
