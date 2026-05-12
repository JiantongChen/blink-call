from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from PIL import Image
from torch.utils.data import ConcatDataset, DataLoader, Dataset
from torchvision import transforms


IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".webp"}


def is_image_file(path: Path) -> bool:
    return path.is_file() and not path.name.startswith(".") and path.suffix.lower() in IMAGE_EXTENSIONS


class EyeImageFolder(Dataset):
    """ImageFolder-style dataset with explicit class-to-label mapping."""

    def __init__(self, root: str | Path, split: str, class_map: dict[str, int], transform=None):
        self.root = Path(root) / split
        self.transform = transform
        self.samples: list[tuple[Path, int]] = []

        if not self.root.exists():
            raise FileNotFoundError(f"Missing split directory: {self.root}")

        for class_dir, label in class_map.items():
            folder = self.root / class_dir
            if not folder.exists():
                raise FileNotFoundError(f"Missing class directory: {folder}")
            for path in sorted(folder.iterdir()):
                if is_image_file(path):
                    self.samples.append((path, int(label)))

        if not self.samples:
            raise RuntimeError(f"No images found under {self.root}")

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, index: int):
        path, label = self.samples[index]
        image = Image.open(path).convert("RGB")
        if self.transform is not None:
            image = self.transform(image)
        return image, label

    @property
    def labels(self) -> list[int]:
        return [label for _, label in self.samples]


def build_transform(image_size: int, train: bool):
    resize = transforms.Resize((image_size, image_size), antialias=True)
    common = [
        resize,
        transforms.ToTensor(),
        transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
    ]
    if not train:
        return transforms.Compose(common)
    return transforms.Compose(
        [
            resize,
            transforms.RandomHorizontalFlip(p=0.5),
            transforms.ToTensor(),
            transforms.Normalize(mean=(0.485, 0.456, 0.406), std=(0.229, 0.224, 0.225)),
        ]
    )


def build_dataset(cfg: dict[str, Any], split: str, train: bool = False) -> Dataset:
    image_size = int(cfg["data"].get("image_size", 224))
    transform = build_transform(image_size=image_size, train=train)
    datasets = [
        EyeImageFolder(
            root=item["root"],
            split=split,
            class_map=item["class_map"],
            transform=transform,
        )
        for item in cfg["data"]["datasets"]
    ]
    return datasets[0] if len(datasets) == 1 else ConcatDataset(datasets)


def label_counts(dataset: Dataset, num_classes: int = 2) -> list[int]:
    labels: list[int] = []
    if isinstance(dataset, ConcatDataset):
        for child in dataset.datasets:
            labels.extend(getattr(child, "labels"))
    else:
        labels.extend(getattr(dataset, "labels"))
    counter = Counter(labels)
    return [counter.get(i, 0) for i in range(num_classes)]


def build_loader(cfg: dict[str, Any], split: str, train: bool = False) -> DataLoader:
    dataset = build_dataset(cfg, split=split, train=train)
    batch_size_key = "batch_size" if train else "eval_batch_size"
    batch_size = int(cfg["data"].get(batch_size_key, cfg["data"].get("batch_size", 64)))
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=train,
        num_workers=int(cfg["data"].get("num_workers", 4)),
        pin_memory=bool(cfg["data"].get("pin_memory", True)),
        drop_last=False,
    )
