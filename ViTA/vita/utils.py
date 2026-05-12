from __future__ import annotations

import json
import random
from pathlib import Path
from typing import Any

import torch
import yaml


CLASS_NAMES = ["closed", "open"]
CLASS_NAME_ALIASES = {"sleepy": "closed", "awake": "open"}


def load_config(path: str | Path) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def save_json(data: dict[str, Any], path: str | Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def class_names_from_config(cfg: dict[str, Any]) -> list[str]:
    if "class_names" in cfg:
        return [str(name) for name in cfg["class_names"]]

    names_by_label: dict[int, str] = {}
    for dataset in cfg["data"]["datasets"]:
        for class_name, label in dataset["class_map"].items():
            canonical_name = CLASS_NAME_ALIASES.get(class_name, class_name)
            label = int(label)
            existing = names_by_label.get(label)
            if existing is not None and existing != canonical_name:
                raise ValueError(
                    f"Conflicting class names for label {label}: {existing}, {canonical_name}"
                )
            names_by_label[label] = canonical_name

    if not names_by_label:
        return list(CLASS_NAMES)

    expected_labels = set(range(max(names_by_label) + 1))
    missing_labels = sorted(expected_labels - set(names_by_label))
    if missing_labels:
        raise ValueError(f"Missing class names for labels: {missing_labels}")
    return [names_by_label[label] for label in sorted(names_by_label)]


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)


def compute_class_weights(counts: list[int], device: torch.device) -> torch.Tensor:
    total = sum(counts)
    if total == 0 or any(c == 0 for c in counts):
        return torch.ones(len(counts), device=device)
    weights = [total / (len(counts) * c) for c in counts]
    return torch.tensor(weights, dtype=torch.float32, device=device)
