from __future__ import annotations

from typing import Any

import timm


def build_model(cfg: dict[str, Any], num_classes: int = 2, pretrained: bool | None = None):
    model_cfg = cfg["model"]
    return timm.create_model(
        model_cfg["name"],
        pretrained=bool(model_cfg.get("pretrained", True) if pretrained is None else pretrained),
        num_classes=num_classes,
        **dict(model_cfg.get("kwargs", {})),
    )
