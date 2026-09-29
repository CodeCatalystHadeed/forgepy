"""Transactional project writes that preserve all pre-existing data."""

import os
import shutil
import tempfile
from pathlib import Path

from forgepy.models import ProjectSpec


class DestinationError(OSError):
    """Raised when a destination cannot safely be used."""


def ensure_destination_available(destination: Path) -> None:
    if destination.is_symlink():
        raise DestinationError(f"Destination cannot be a symbolic link: {destination}")
    if destination.exists() and destination.is_file():
        raise DestinationError(f"Destination is a file: {destination}")
    if destination.exists() and any(destination.iterdir()):
        raise DestinationError(f"Destination is not empty: {destination}")


def _inside(root: Path, candidate: Path) -> bool:
    try:
        candidate.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def write_project(destination: Path, spec: ProjectSpec) -> None:
    """Stage a complete tree, then move its files into an empty destination."""
    ensure_destination_available(destination)
    parent = destination.parent.resolve()
    parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".forgepy-", dir=parent))
    destination_existed = destination.exists()
    try:
        for item in spec.files:
            target = stage.joinpath(*item.path.split("/"))
            if not _inside(stage, target):
                raise DestinationError(f"Template path escapes destination: {item.path}")
            target.parent.mkdir(parents=True, exist_ok=True)
            if isinstance(item.content, bytes):
                target.write_bytes(item.content)
            else:
                target.write_text(item.content, encoding="utf-8", newline="\n")
        if destination_existed:
            # Replacing the empty directory as one unit avoids a half-moved tree.
            destination.rmdir()
            try:
                os.replace(stage, destination)
            except Exception:
                destination.mkdir(exist_ok=True)
                raise
        else:
            os.replace(stage, destination)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise
