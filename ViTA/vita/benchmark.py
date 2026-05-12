from __future__ import annotations

import argparse
import time
from pathlib import Path

import torch
from torch.amp import autocast

from .models import build_model
from .utils import class_names_from_config, load_config, save_json


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Measure model inference throughput.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument("--checkpoint", default=None, help="Optional checkpoint path.")
    parser.add_argument("--device", default="cuda", choices=["cuda", "cpu"])
    parser.add_argument("--batch-size", type=int, default=1)
    parser.add_argument("--warmup", type=int, default=20)
    parser.add_argument("--steps", type=int, default=100)
    parser.add_argument("--threads", type=int, default=None, help="Optional CPU thread count.")
    parser.add_argument("--output", default=None, help="Optional metrics JSON path.")
    return parser.parse_args()


@torch.inference_mode()
def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    class_names = class_names_from_config(cfg)
    device = torch.device(args.device if args.device == "cpu" or torch.cuda.is_available() else "cpu")
    if args.threads is not None:
        torch.set_num_threads(args.threads)
    image_size = int(cfg["data"].get("image_size", 224))

    checkpoint = None
    if args.checkpoint:
        checkpoint = torch.load(args.checkpoint, map_location=device)
        if "class_names" in checkpoint:
            class_names = [str(name) for name in checkpoint["class_names"]]
    model = build_model(cfg, num_classes=len(class_names), pretrained=False).to(device)
    if checkpoint is not None:
        model.load_state_dict(checkpoint["model"])
    model.eval()

    x = torch.randn(args.batch_size, 3, image_size, image_size, device=device)
    amp = bool(cfg["train"].get("amp", True)) and device.type == "cuda"

    for _ in range(args.warmup):
        with autocast(device_type=device.type, enabled=amp):
            _ = model(x)
    if device.type == "cuda":
        torch.cuda.synchronize()

    started = time.perf_counter()
    for _ in range(args.steps):
        with autocast(device_type=device.type, enabled=amp):
            _ = model(x)
    if device.type == "cuda":
        torch.cuda.synchronize()
    elapsed = time.perf_counter() - started

    images = args.batch_size * args.steps
    fps = images / elapsed
    metrics = {
        "fps": fps,
        "latency_ms_per_image": elapsed * 1000.0 / images,
        "elapsed_seconds": elapsed,
        "images": images,
        "batch_size": args.batch_size,
        "steps": args.steps,
        "image_size": image_size,
        "device": device.type,
        "threads": torch.get_num_threads() if device.type == "cpu" else None,
    }
    print(f"FPS: {fps:.2f}")
    if args.output:
        save_json(metrics, Path(args.output))


if __name__ == "__main__":
    main()
