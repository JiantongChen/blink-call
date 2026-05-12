from __future__ import annotations

import argparse
import csv
import time
from pathlib import Path
from typing import Any

import torch
from torch import nn
from torch.amp import GradScaler, autocast
from tqdm import tqdm

from .data import build_loader, label_counts
from .models import build_model
from .utils import (
    class_names_from_config,
    compute_class_weights,
    load_config,
    save_json,
    set_seed,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train an eye-state classifier.")
    parser.add_argument("--config", required=True, help="Path to YAML config.")
    parser.add_argument("--device", default=None, help="Override device, e.g. cuda or cpu.")
    return parser.parse_args()


def run_epoch(
    model: nn.Module,
    loader,
    criterion: nn.Module,
    device: torch.device,
    optimizer: torch.optim.Optimizer | None = None,
    scaler: GradScaler | None = None,
    amp: bool = False,
) -> tuple[float, float]:
    training = optimizer is not None
    model.train(training)
    total_loss = 0.0
    total_samples = 0
    correct_samples = 0

    iterator = tqdm(loader, leave=False, desc="train" if training else "val")
    with torch.set_grad_enabled(training):
        for images, targets in iterator:
            images = images.to(device, non_blocking=True)
            targets = targets.to(device, non_blocking=True)

            if training:
                optimizer.zero_grad(set_to_none=True)

            with autocast(device_type=device.type, enabled=amp and device.type == "cuda"):
                logits = model(images)
                loss = criterion(logits, targets)

            if training:
                assert scaler is not None
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()

            batch_size = targets.size(0)
            total_loss += float(loss.detach().cpu()) * batch_size
            total_samples += batch_size
            preds = logits.argmax(dim=1)
            correct_samples += int((preds == targets).sum().detach().cpu())
            iterator.set_postfix(
                loss=total_loss / max(total_samples, 1),
                acc=correct_samples / max(total_samples, 1),
            )

    return total_loss / max(total_samples, 1), correct_samples / max(total_samples, 1)


def save_checkpoint(
    path: Path,
    cfg: dict[str, Any],
    class_names: list[str],
    model: nn.Module,
    optimizer: torch.optim.Optimizer,
    epoch: int,
    metrics: dict[str, float],
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "config": cfg,
            "class_names": class_names,
            "epoch": epoch,
            "model": model.state_dict(),
            "optimizer": optimizer.state_dict(),
            "metrics": metrics,
        },
        path,
    )


def main() -> None:
    args = parse_args()
    cfg = load_config(args.config)
    class_names = class_names_from_config(cfg)
    set_seed(int(cfg.get("seed", 42)))

    device_name = args.device or cfg["train"].get("device", "cuda")
    device = torch.device(device_name if torch.cuda.is_available() or device_name == "cpu" else "cpu")
    output_dir = Path(cfg.get("output_dir", "outputs")) / cfg.get("experiment_name", "eye_cls")
    output_dir.mkdir(parents=True, exist_ok=True)
    save_json(cfg, output_dir / "config.json")

    train_loader = build_loader(cfg, split="train", train=True)
    val_loader = build_loader(cfg, split="val", train=False)
    model = build_model(cfg, num_classes=len(class_names)).to(device)

    counts = label_counts(train_loader.dataset, num_classes=len(class_names))
    class_weights = None
    if bool(cfg["train"].get("class_weight", True)):
        class_weights = compute_class_weights(counts, device=device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)

    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(cfg["train"].get("lr", 5e-5)),
        weight_decay=float(cfg["train"].get("weight_decay", 0.05)),
    )
    epochs = int(cfg["train"].get("epochs", 20))
    warmup_epochs = int(cfg["train"].get("warmup_epochs", 0))
    if warmup_epochs > 0:
        warmup = torch.optim.lr_scheduler.LinearLR(
            optimizer, start_factor=0.01, total_iters=warmup_epochs
        )
        cosine = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer, T_max=max(epochs - warmup_epochs, 1)
        )
        scheduler = torch.optim.lr_scheduler.SequentialLR(
            optimizer, schedulers=[warmup, cosine], milestones=[warmup_epochs]
        )
    else:
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
    amp = bool(cfg["train"].get("amp", True))
    scaler = GradScaler("cuda", enabled=amp and device.type == "cuda")

    best_score = -1.0
    history_path = output_dir / "metrics.csv"
    with history_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "epoch",
                "lr",
                "train_loss",
                "train_accuracy",
                "val_loss",
                "val_accuracy",
                "seconds",
            ],
        )
        writer.writeheader()

        for epoch in range(1, epochs + 1):
            started = time.perf_counter()
            train_loss, train_acc = run_epoch(
                model, train_loader, criterion, device, optimizer=optimizer, scaler=scaler, amp=amp
            )
            val_loss, val_acc = run_epoch(model, val_loader, criterion, device, amp=amp)
            scheduler.step()

            score = float(val_acc)
            val_metrics = {"accuracy": val_acc}
            if score > best_score:
                best_score = score
                save_checkpoint(
                    output_dir / "best.pt", cfg, class_names, model, optimizer, epoch, val_metrics
                )
            save_checkpoint(output_dir / "last.pt", cfg, class_names, model, optimizer, epoch, val_metrics)

            row = {
                "epoch": epoch,
                "lr": optimizer.param_groups[0]["lr"],
                "train_loss": train_loss,
                "train_accuracy": train_acc,
                "val_loss": val_loss,
                "val_accuracy": val_acc,
                "seconds": time.perf_counter() - started,
            }
            writer.writerow(row)
            f.flush()
            print(
                "epoch={} train_loss={:.4f} train_acc={:.4f} "
                "val_loss={:.4f} val_acc={:.4f}".format(
                    epoch, train_loss, train_acc, val_loss, val_acc
                )
            )

    print("best_accuracy={:.4f}".format(best_score))
    print("output_dir={}".format(output_dir))


if __name__ == "__main__":
    main()
