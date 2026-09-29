"""Core template and generated-project data models."""

import re
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import PurePosixPath

from forgepy.config import ProjectConfig


class TemplateError(ValueError):
    """Raised when a template specification is malformed."""


_INVALID_PATH_CHARS = re.compile(r'[<>:"|?*\x00-\x1f]')
_WINDOWS_RESERVED = {"CON", "PRN", "AUX", "NUL", *(f"COM{i}" for i in range(1, 10)), *(f"LPT{i}" for i in range(1, 10))}


@dataclass(frozen=True, slots=True)
class ProjectFile:
    path: str
    content: str | bytes

    def __post_init__(self) -> None:
        path = PurePosixPath(self.path)
        if (
            not self.path
            or "\\" in self.path
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
            or any(_INVALID_PATH_CHARS.search(part) for part in path.parts)
            or any(part.split(".")[0].upper() in _WINDOWS_RESERVED for part in path.parts)
        ):
            raise TemplateError(f"Unsafe template path: {self.path!r}")


@dataclass(frozen=True, slots=True)
class ProjectSpec:
    files: tuple[ProjectFile, ...]
    dependencies: tuple[str, ...]
    next_commands: tuple[str, ...]
    start_files: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        paths = [item.path for item in self.files]
        if len(paths) != len(set(paths)):
            raise TemplateError("A project specification contains duplicate file paths")


Builder = Callable[[ProjectConfig], ProjectSpec]


@dataclass(frozen=True, slots=True)
class Template:
    id: str
    display_name: str
    description: str
    builder: Builder = field(repr=False)
    supports_provider: bool = False
    supports_vector_store: bool = False
    supports_api: bool = False

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", self.id):
            raise TemplateError(f"Invalid template ID: {self.id!r}")
        if not self.display_name.strip() or not self.description.strip() or not callable(self.builder):
            raise TemplateError(f"Malformed template metadata for {self.id!r}")


class TemplateRegistry:
    """Small explicit registry; core generation never branches on template IDs."""

    def __init__(self) -> None:
        self._items: dict[str, Template] = {}

    def register(self, template: Template) -> None:
        if template.id in self._items:
            raise TemplateError(f"Duplicate template ID: {template.id}")
        self._items[template.id] = template

    def get(self, template_id: str) -> Template:
        try:
            return self._items[template_id]
        except KeyError as exc:
            choices = ", ".join(self._items)
            raise TemplateError(f"Unknown template {template_id!r}. Choose from: {choices}") from exc

    def all(self) -> tuple[Template, ...]:
        return tuple(self._items.values())

    def as_mapping(self) -> Mapping[str, Template]:
        return dict(self._items)
