"""Inspect ForgePy wheel and sdist contents without installing them."""

from __future__ import annotations

import argparse
import email
import glob
import tarfile
import zipfile
from pathlib import Path, PurePosixPath

REQUIRED_MODULES = {
    "forgepy/__init__.py",
    "forgepy/__main__.py",
    "forgepy/cli.py",
    "forgepy/config.py",
    "forgepy/generator.py",
    "forgepy/models.py",
    "forgepy/setup.py",
    "forgepy/registry/__init__.py",
    "forgepy/registry/templates.py",
    "forgepy/templates/__init__.py",
    "forgepy/templates/builders.py",
    "forgepy/templates/shared.py",
    "forgepy/utils/__init__.py",
    "forgepy/utils/filesystem.py",
    "forgepy/utils/naming.py",
}
FORBIDDEN_PARTS = {".git", ".github", ".pytest_cache", ".ruff_cache", "__pycache__", ".venv", "dist"}
FORBIDDEN_SUFFIXES = {".pyc", ".pyo", ".pem", ".key"}


def _assert_safe(names: set[str]) -> None:
    for name in names:
        path = PurePosixPath(name)
        assert not (set(path.parts) & FORBIDDEN_PARTS), f"unexpected packaged path: {name}"
        assert path.suffix.lower() not in FORBIDDEN_SUFFIXES, f"unexpected packaged file: {name}"
        assert path.name != ".env", f"secret-bearing environment file packaged: {name}"


def _validate_wheel(path: Path) -> None:
    with zipfile.ZipFile(path) as archive:
        names = set(archive.namelist())
        _assert_safe(names)
        missing = REQUIRED_MODULES - names
        assert not missing, f"wheel is missing modules: {sorted(missing)}"
        metadata_name = next(name for name in names if name.endswith(".dist-info/METADATA"))
        entry_points_name = next(name for name in names if name.endswith(".dist-info/entry_points.txt"))
        license_name = next(name for name in names if name.endswith(".dist-info/licenses/LICENSE"))
        metadata = email.message_from_bytes(archive.read(metadata_name))
        assert metadata["Name"] == "forgepy"
        assert metadata["Version"] == "1.0.0"
        assert metadata["License-Expression"] == "MIT"
        assert metadata.get_all("License-File") == ["LICENSE"]
        assert "forgepy = forgepy.cli:app" in archive.read(entry_points_name).decode("utf-8")
        assert archive.read(license_name).startswith(b"MIT License")


def _validate_sdist(path: Path) -> None:
    with tarfile.open(path, "r:gz") as archive:
        names = {member.name for member in archive.getmembers() if member.isfile()}
        _assert_safe(names)
        roots = {PurePosixPath(name).parts[0] for name in names}
        assert len(roots) == 1, f"sdist must have one root directory: {sorted(roots)}"
        root = roots.pop()
        required = {
            f"{root}/pyproject.toml",
            f"{root}/README.md",
            f"{root}/LICENSE",
            f"{root}/scripts/validate_dist.py",
            *(f"{root}/src/{module}" for module in REQUIRED_MODULES),
        }
        missing = required - names
        assert not missing, f"sdist is missing rebuild/runtime files: {sorted(missing)}"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifacts", nargs="+", type=Path)
    args = parser.parse_args()
    artifacts = [Path(match) for value in args.artifacts for match in (glob.glob(str(value)) or [str(value)])]
    wheels = [path for path in artifacts if path.suffix == ".whl"]
    sdists = [path for path in artifacts if path.name.endswith(".tar.gz")]
    assert len(wheels) == 1, f"expected exactly one wheel, found {len(wheels)}"
    assert len(sdists) == 1, f"expected exactly one sdist, found {len(sdists)}"
    _validate_wheel(wheels[0])
    _validate_sdist(sdists[0])
    print(f"Validated {wheels[0]} and {sdists[0]}")


if __name__ == "__main__":
    main()
