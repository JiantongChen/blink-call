from __future__ import annotations

import argparse
from pathlib import Path

import torch
from torch import nn
from torch.amp import autocast
from tqdm import tqdm

from .data import build_loader
from .models import build_model
from .utils import class_names_from_config, load_config, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate an eye-state classifier.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument("--checkpoint", required=True, help="Path to checkpoint.")
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--device", default=None, help="Override device, e.g. cuda or cpu.")
    parser.add_argument("--output", default=None, help="Optional metrics JSON path.")
    return parser.parse_args()


@torch.inference_mode()
def evaluate(
    model: nn.Module,
    loader,
    device: torch.device,
    amp: bool,
    class_names: list[str],
) -> dict:
    model.eval()
    num_classes = len(class_names)
    confusion = torch.zeros(num_classes, num_classes, dtype=torch.long)
    correct = 0
    total = 0
    for images, targets in tqdm(loader, leave=False, desc="eval"):
        images = images.to(device, non_blocking=True)
        targets = targets.to(device, non_blocking=True)
        with autocast(device_type=device.type, enabled=amp and device.type == "cuda"):
            logits = model(images)
        preds = logits.argmax(dim=1)
        for target, pred in zip(targets.detach().cpu(), preds.detach().cpu()):
            confusion[int(target), int(pred)] += 1
        correct += int((preds == targets).sum().detach().cpu())
        total += targets.size(0)

    per_class_accuracy = {}
    for index, class_name in enumerate(class_names):
        class_total = int(confusion[index].sum())
        per_class_accuracy[class_name] = (
            float(confusion[index, index]) / class_total if class_total > 0 else 0.0
        )
    return {
        "accuracy": correct / max(total, 1),
        "class_names": class_names,
        "per_class_accuracy": per_class_accuracy,
        "confusion_matrix": confusion.tolist(),
    }


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    class_names = class_names_from_config(cfg)
    device_name = args.device or cfg["train"].get("device", "cuda")
    device = torch.device(device_name if torch.cuda.is_available() or device_name == "cpu" else "cpu")

    checkpoint = torch.load(args.checkpoint, map_location=device)
    if "class_names" in checkpoint:
        class_names = [str(name) for name in checkpoint["class_names"]]
    model = build_model(cfg, num_classes=len(class_names), pretrained=False).to(device)
    model.load_state_dict(checkpoint["model"])

    loader = build_loader(cfg, split=args.split, train=False)
    metrics = evaluate(
        model,
        loader,
        device,
        amp=bool(cfg["train"].get("amp", True)),
        class_names=class_names,
    )
    print(f"ACC: {metrics['accuracy']:.4f}")

    if args.output:
        save_json(metrics, Path(args.output))


if __name__ == "__main__":
    main()
