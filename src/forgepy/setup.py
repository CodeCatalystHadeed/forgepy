"""Optional post-generation environment setup and local verification."""

import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from forgepy.config import PackageManager, ProjectConfig


class SetupError(RuntimeError):
    """Raised after generation when an environment setup command fails."""

    def __init__(self, command: str, reason: str) -> None:
        super().__init__(reason)
        self.command = command


@dataclass(frozen=True, slots=True)
class SetupResult:
    commands: tuple[str, ...]
    environment_file_created: bool


def _display(command: list[str]) -> str:
    return subprocess.list2cmdline(command) if os.name == "nt" else shlex.join(command)


def _run(command: list[str], destination: Path) -> str:
    rendered = _display(command)
    try:
        subprocess.run(command, cwd=destination, check=True)
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SetupError(rendered, str(exc)) from exc
    return rendered


def _source_roots(destination: Path) -> tuple[str, ...]:
    return tuple(name for name in ("app", "src") if (destination / name).is_dir())


def _prepare_environment_file(destination: Path) -> bool:
    example = destination / ".env.example"
    environment = destination / ".env"
    if example.is_file() and not environment.exists():
        shutil.copyfile(example, environment)
        return True
    return False


def setup_project(config: ProjectConfig) -> SetupResult:
    """Create an environment, install selected dependencies, and verify the starter."""
    destination = config.destination
    commands: list[str] = []
    try:
        environment_created = _prepare_environment_file(destination)
    except OSError as exc:
        command = "Copy-Item .env.example .env" if os.name == "nt" else "cp .env.example .env"
        raise SetupError(command, str(exc)) from exc
    roots = _source_roots(destination)

    if config.package_manager is PackageManager.UV:
        sync = ["uv", "sync"]
        if config.include_tests:
            sync.extend(("--extra", "dev"))
        commands.append(_run(sync, destination))
        if roots:
            commands.append(_run(["uv", "run", "python", "-m", "compileall", "-q", *roots], destination))
        if config.include_tests:
            commands.append(_run(["uv", "run", "pytest", "-q"], destination))
    else:
        commands.append(_run([sys.executable, "-m", "venv", ".venv"], destination))
        environment_python = destination / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        install_target = ".[dev]" if config.include_tests else "."
        commands.append(_run([str(environment_python), "-m", "pip", "install", "-e", install_target], destination))
        if roots:
            commands.append(_run([str(environment_python), "-m", "compileall", "-q", *roots], destination))
        if config.include_tests:
            commands.append(_run([str(environment_python), "-m", "pytest", "-q"], destination))

    return SetupResult(tuple(commands), environment_created)
