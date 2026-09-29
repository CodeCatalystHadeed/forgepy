"""Project-name validation and normalization."""

import keyword
import re
from pathlib import PurePath

WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
}
INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
MAX_PROJECT_NAME_LENGTH = 100


class InvalidProjectName(ValueError):
    """Raised when a project name could escape or break the destination."""


def validate_project_name(name: str) -> str:
    if not name or name != name.strip():
        raise InvalidProjectName("Project name cannot be empty or have surrounding whitespace")
    if len(name) > MAX_PROJECT_NAME_LENGTH:
        raise InvalidProjectName(f"Project name cannot exceed {MAX_PROJECT_NAME_LENGTH} characters")
    if name in {".", ".."} or PurePath(name).is_absolute():
        raise InvalidProjectName("Project name must be a simple relative name")
    if INVALID_CHARS.search(name) or "/" in name or "\\" in name:
        raise InvalidProjectName("Project name contains an invalid filesystem character")
    if name.endswith((".", " ")):
        raise InvalidProjectName("Project name cannot end with a dot or space")
    if name.split(".")[0].upper() in WINDOWS_RESERVED:
        raise InvalidProjectName("Project name is reserved by Windows")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._ -]*", name):
        raise InvalidProjectName("Use letters, numbers, spaces, dots, hyphens, or underscores")
    return name


def distribution_name(name: str) -> str:
    validate_project_name(name)
    normalized = re.sub(r"[\s_.]+", "-", name).lower()
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if not normalized:
        raise InvalidProjectName("Project name cannot normalize to an empty name")
    return normalized


def import_name(name: str) -> str:
    validate_project_name(name)
    normalized = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    if not normalized:
        raise InvalidProjectName("Project name cannot normalize to an import name")
    if normalized[0].isdigit():
        normalized = f"project_{normalized}"
    if keyword.iskeyword(normalized):
        normalized += "_project"
    return normalized
