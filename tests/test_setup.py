import subprocess
from pathlib import Path

import pytest

from forgepy.config import PackageManager, ProjectConfig
from forgepy.setup import SetupError, setup_project


def config(destination: Path, manager: PackageManager, *, tests: bool = True) -> ProjectConfig:
    return ProjectConfig(
        project_name="sample",
        package_name="sample",
        destination=destination,
        template_id="fastapi",
        package_manager=manager,
        include_tests=tests,
    )


def test_uv_setup_installs_compiles_tests_and_copies_environment(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "app").mkdir()
    (tmp_path / ".env.example").write_text("APP_NAME=Example\n")
    calls: list[list[str]] = []

    def succeed(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("forgepy.setup.subprocess.run", succeed)
    result = setup_project(config(tmp_path, PackageManager.UV))
    assert calls == [
        ["uv", "sync", "--extra", "dev"],
        ["uv", "run", "python", "-m", "compileall", "-q", "app"],
        ["uv", "run", "pytest", "-q"],
    ]
    assert result.environment_file_created
    assert (tmp_path / ".env").read_text() == "APP_NAME=Example\n"


def test_pip_setup_uses_the_created_environment(monkeypatch, tmp_path: Path) -> None:
    (tmp_path / "src").mkdir()
    calls: list[list[str]] = []

    def succeed(command, **kwargs):
        calls.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr("forgepy.setup.subprocess.run", succeed)
    setup_project(config(tmp_path, PackageManager.PIP, tests=False))
    assert calls[0][-3:] == ["-m", "venv", ".venv"]
    assert calls[1][-5:] == ["-m", "pip", "install", "-e", "."]
    assert "compileall" in calls[2]
    assert all("pytest" not in command for command in calls)


def test_setup_failure_reports_the_exact_recovery_command(monkeypatch, tmp_path: Path) -> None:
    def fail(command, **kwargs):
        raise subprocess.CalledProcessError(1, command)

    monkeypatch.setattr("forgepy.setup.subprocess.run", fail)
    with pytest.raises(SetupError) as raised:
        setup_project(config(tmp_path, PackageManager.UV))
    assert raised.value.command == "uv sync --extra dev"
