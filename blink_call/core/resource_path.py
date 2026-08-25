from pathlib import Path

from PySide6.QtCore import QCoreApplication


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def get_resource_path(*parts: str) -> Path:
    """Return a resource path that works in source and standalone builds."""
    relative_path = Path(*parts)
    candidates = [
        Path(QCoreApplication.applicationDirPath()) / relative_path,
        PROJECT_ROOT / relative_path,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    return candidates[0].resolve()
