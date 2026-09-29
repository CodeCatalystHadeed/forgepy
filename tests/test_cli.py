from pathlib import Path

from typer.testing import CliRunner

from forgepy import __version__
from forgepy.cli import app
from forgepy.setup import SetupError, SetupResult

runner = CliRunner()


def test_help() -> None:
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "create" in result.stdout


def test_version() -> None:
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


def test_create_help_lists_options() -> None:
    result = runner.invoke(app, ["create", "--help"])
    assert result.exit_code == 0
    assert "--template" in result.stdout
    assert "--no-interactive" in result.stdout
    assert "--guidance" in result.stdout
    assert "--setup" in result.stdout


def test_invalid_command_fails_cleanly() -> None:
    result = runner.invoke(app, ["missing-command"])
    assert result.exit_code != 0
    assert "No such command" in result.output


def test_noninteractive_create(tmp_path: Path) -> None:
    destination = tmp_path / "created"
    result = runner.invoke(
        app, ["create", "My API", "--template", "fastapi", "--no-interactive", "--output", str(destination)]
    )
    assert result.exit_code == 0, result.output
    assert (destination / "app/main.py").exists()
    assert "Project created successfully" in result.stdout
    assert "You're ready to build" in result.stdout
    assert "app/services/items.py" in result.stdout
    assert "python -m venv .venv" in result.stdout
    assert 'python -m pip install -e ".[dev]"' in result.stdout


def test_uv_success_output_uses_uv_run(tmp_path: Path) -> None:
    destination = tmp_path / "uv-project"
    result = runner.invoke(
        app,
        [
            "create",
            "uv-project",
            "--template",
            "cli",
            "--package-manager",
            "uv",
            "--no-interactive",
            "--output",
            str(destination),
        ],
    )
    assert result.exit_code == 0, result.output
    assert "uv sync --extra dev" in result.stdout
    assert "uv run uv-project hello Ada" in result.stdout


def test_learning_and_minimal_cli_experience(tmp_path: Path) -> None:
    learning = tmp_path / "learning"
    result = runner.invoke(
        app,
        [
            "create",
            "learn",
            "--template",
            "langgraph",
            "--guidance",
            "learning",
            "--no-interactive",
            "-o",
            str(learning),
        ],
    )
    assert result.exit_code == 0, result.output
    assert (learning / "PROJECT_GUIDE.md").is_file()
    assert "Read PROJECT_GUIDE.md" in result.stdout

    minimal = tmp_path / "minimal"
    result = runner.invoke(
        app,
        ["create", "quick", "--template", "cli", "--guidance", "minimal", "--no-interactive", "-o", str(minimal)],
    )
    assert result.exit_code == 0, result.output
    assert "Generated tests" not in result.stdout
    assert "## Architecture" not in (minimal / "README.md").read_text()


def test_setup_success_is_reported_without_repeating_install_steps(monkeypatch, tmp_path: Path) -> None:
    destination = tmp_path / "setup"
    monkeypatch.setattr("forgepy.cli.setup_project", lambda config: SetupResult(("verified",), False))
    result = runner.invoke(
        app,
        ["create", "setup", "--template", "fastapi", "--setup", "--no-interactive", "-o", str(destination)],
    )
    assert result.exit_code == 0, result.output
    assert "Installed dependencies and verified" in result.stdout
    assert "python -m venv" not in result.stdout
    assert "Activate.ps1" in result.stdout or "source .venv/bin/activate" in result.stdout


def test_setup_failure_preserves_project_and_gives_recovery(monkeypatch, tmp_path: Path) -> None:
    destination = tmp_path / "setup-failure"

    def fail(config):
        raise SetupError("uv sync --extra dev", "network unavailable")

    monkeypatch.setattr("forgepy.cli.setup_project", fail)
    result = runner.invoke(
        app,
        [
            "create",
            "setup-failure",
            "--template",
            "cli",
            "--package-manager",
            "uv",
            "--setup",
            "--no-interactive",
            "-o",
            str(destination),
        ],
    )
    assert result.exit_code == 1
    assert (destination / "pyproject.toml").is_file()
    assert "Project generated, but automatic setup did not finish" in result.output
    assert "uv sync --extra dev" in result.output
    assert "Project created successfully" not in result.output


def test_invalid_guidance_fails_cleanly(tmp_path: Path) -> None:
    result = runner.invoke(
        app,
        ["create", "x", "--template", "cli", "--guidance", "verbose", "--no-interactive", "-o", str(tmp_path / "x")],
    )
    assert result.exit_code != 0
    assert "learning, standard, or minimal" in result.output


def test_noninteractive_requires_name_and_template() -> None:
    result = runner.invoke(app, ["create", "--no-interactive"])
    assert result.exit_code != 0
    assert "required" in result.output


def test_invalid_name_has_no_traceback(tmp_path: Path) -> None:
    result = runner.invoke(
        app, ["create", "../escape", "--template", "cli", "--no-interactive", "--output", str(tmp_path / "x")]
    )
    assert result.exit_code == 1
    assert "Error:" in result.output
    assert "Traceback" not in result.output


def test_interactive_create_can_complete(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr("forgepy.cli._ask_text", lambda message: "interactive-app")
    monkeypatch.setattr("forgepy.cli._template_choice", lambda: "cli")
    monkeypatch.setattr("forgepy.cli._ask_select", lambda message, choices: choices[0])
    monkeypatch.setattr("forgepy.cli._ask_confirm", lambda message, default: default)
    destination = tmp_path / "interactive"
    result = runner.invoke(app, ["create", "--output", str(destination)])
    assert result.exit_code == 0, result.output
    assert (destination / "src/interactive_app/cli.py").exists()


def test_ctrl_c_cancels_cleanly(monkeypatch, tmp_path: Path) -> None:
    def interrupt(message):
        raise KeyboardInterrupt

    monkeypatch.setattr("forgepy.cli._ask_text", interrupt)
    result = runner.invoke(app, ["create", "--output", str(tmp_path / "cancelled")])
    assert result.exit_code == 130
    assert "Cancelled" in result.output
    assert "Traceback" not in result.output


def test_unsupported_options_are_rejected(tmp_path: Path) -> None:
    cases = [
        ["--provider", "none"],
        ["--vector-store", "none"],
        ["--without-api"],
    ]
    for index, options in enumerate(cases):
        result = runner.invoke(
            app,
            [
                "create",
                "x",
                "--template",
                "fastapi",
                "--no-interactive",
                "--output",
                str(tmp_path / str(index)),
                *options,
            ],
        )
        assert result.exit_code != 0
        assert "does not support" in result.output


def test_invalid_feature_values_fail_cleanly(tmp_path: Path) -> None:
    for option in ("--provider", "--vector-store"):
        result = runner.invoke(
            app,
            [
                "create",
                "x",
                "--template",
                "rag",
                "--no-interactive",
                "--output",
                str(tmp_path / option.removeprefix("--")),
                option,
                "invalid",
            ],
        )
        assert result.exit_code != 0
        assert "choose one of" in result.output
        assert "Traceback" not in result.output


def test_unexpected_generation_failure_has_no_success_or_traceback(monkeypatch, tmp_path: Path) -> None:
    def fail(*args, **kwargs):
        raise RuntimeError("simulated renderer failure")

    monkeypatch.setattr("forgepy.cli.generate", fail)
    result = runner.invoke(
        app, ["create", "x", "--template", "cli", "--no-interactive", "--output", str(tmp_path / "x")]
    )
    assert result.exit_code == 1
    assert "simulated renderer failure" in result.output
    assert "Project created successfully" not in result.output
    assert "Traceback" not in result.output
