"""Command-line interface; prompting is kept separate from generation."""

import os
from pathlib import Path
from typing import Annotated

import questionary
import typer
from rich.console import Console
from rich.panel import Panel

from forgepy import __version__
from forgepy.config import Guidance, PackageManager, ProjectConfig, Provider, VectorStore
from forgepy.generator import generate
from forgepy.models import TemplateError
from forgepy.registry import registry
from forgepy.setup import SetupError, SetupResult, setup_project
from forgepy.utils.filesystem import DestinationError
from forgepy.utils.naming import InvalidProjectName, distribution_name, import_name

app = typer.Typer(
    name="forgepy",
    help="Create clean Python backend, AI, data, ML, and CLI projects.",
    no_args_is_help=True,
    rich_markup_mode="markdown",
)
console = Console()
error_console = Console(stderr=True)


def _version(value: bool) -> None:
    if value:
        typer.echo(f"forgepy {__version__}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        bool,
        typer.Option("--version", callback=_version, is_eager=True, help="Show the version and exit."),
    ] = False,
) -> None:
    """Generate a modern Python project without unsafe overwrites."""


def _ask_text(message: str) -> str:
    value = questionary.text(message).ask()
    if value is None:
        raise typer.Abort()
    return value


def _ask_select(message: str, choices: list[object]) -> object:
    value = questionary.select(message, choices=choices).ask()
    if value is None:
        raise typer.Abort()
    return value


def _ask_confirm(message: str, default: bool) -> bool:
    value = questionary.confirm(message, default=default).ask()
    if value is None:
        raise typer.Abort()
    return bool(value)


def _template_choice() -> str:
    choices = [
        questionary.Choice(f"{item.display_name} - {item.description}", value=item.id) for item in registry.all()
    ]
    return str(_ask_select("Project type:", choices))


def _enum_value(enum_type: type[Provider] | type[VectorStore], value: str, option: str):
    try:
        return enum_type(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_type)
        raise typer.BadParameter(f"choose one of: {allowed}", param_hint=option) from exc


def _resolve_config(
    name: str | None,
    template_id: str | None,
    python_version: str | None,
    package_manager: str | None,
    include_tests: bool | None,
    include_docker: bool | None,
    provider: str | None,
    vector_store: str | None,
    include_api: bool | None,
    guidance: str | None,
    run_setup: bool | None,
    no_interactive: bool,
    output: Path | None,
) -> ProjectConfig:
    if no_interactive and (not name or not template_id):
        raise typer.BadParameter("PROJECT_NAME and --template are required with --no-interactive")
    if not name:
        name = _ask_text("Project name:")
    dist_name = distribution_name(name)
    package_name = import_name(name)

    if not template_id:
        template_id = _template_choice()
    template = registry.get(template_id)
    if not python_version:
        python_version = "3.12" if no_interactive else str(_ask_select("Python version:", ["3.12", "3.11"]))
    if python_version not in {"3.11", "3.12"}:
        raise typer.BadParameter("supported versions are 3.11 and 3.12", param_hint="--python")
    if not package_manager:
        package_manager = "pip" if no_interactive else str(_ask_select("Package manager:", ["pip", "uv"]))
    try:
        manager = PackageManager(package_manager)
    except ValueError as exc:
        raise typer.BadParameter("choose pip or uv", param_hint="--package-manager") from exc

    if guidance is None and not no_interactive:
        guidance = str(_ask_select("Guidance level:", [item.value for item in Guidance]))
    try:
        selected_guidance = Guidance(guidance or Guidance.STANDARD)
    except ValueError as exc:
        raise typer.BadParameter("choose learning, standard, or minimal", param_hint="--guidance") from exc

    tests = True if include_tests is None and no_interactive else include_tests
    docker = False if include_docker is None and no_interactive else include_docker
    if tests is None:
        tests = _ask_confirm("Include tests?", True)
    if docker is None:
        docker = _ask_confirm("Include Docker?", False)

    selected_provider = Provider.NONE
    if template.supports_provider:
        if provider is None and not no_interactive:
            provider = str(_ask_select("Model provider:", [item.value for item in Provider]))
        selected_provider = _enum_value(Provider, provider or "none", "--provider")
    elif provider is not None:
        raise typer.BadParameter(f"template {template.id!r} does not support model providers", param_hint="--provider")

    selected_store = VectorStore.NONE
    if template.supports_vector_store:
        if vector_store is None and not no_interactive:
            vector_store = str(_ask_select("Vector store:", [item.value for item in VectorStore]))
        selected_store = _enum_value(VectorStore, vector_store or "none", "--vector-store")
    elif vector_store is not None:
        raise typer.BadParameter(
            f"template {template.id!r} does not support vector stores", param_hint="--vector-store"
        )

    api = False
    if template.supports_api:
        api = (
            bool(include_api)
            if include_api is not None
            else (False if no_interactive else _ask_confirm("Include FastAPI API?", False))
        )
    elif include_api is not None:
        raise typer.BadParameter(f"template {template.id!r} does not support an API option", param_hint="--with-api")

    setup = False if run_setup is None and no_interactive else run_setup
    if setup is None:
        setup = _ask_confirm("Create the environment, install dependencies, and run verification now?", False)

    destination = output.expanduser() if output else Path.cwd() / name
    return ProjectConfig(
        dist_name,
        package_name,
        destination,
        template.id,
        python_version,
        manager,
        bool(tests),
        bool(docker),
        selected_provider,
        selected_store,
        api,
        selected_guidance,
        bool(setup),
    )


@app.command()
def create(
    project_name: Annotated[str | None, typer.Argument(help="Project directory/name to create.")] = None,
    template: Annotated[str | None, typer.Option("--template", "-t", help="Template ID (see --help).")] = None,
    python_version: Annotated[str | None, typer.Option("--python", help="Python version: 3.11 or 3.12.")] = None,
    package_manager: Annotated[str | None, typer.Option("--package-manager", "-p", help="pip or uv.")] = None,
    include_tests: Annotated[
        bool | None, typer.Option("--with-tests/--without-tests", help="Include starter tests.")
    ] = None,
    include_docker: Annotated[
        bool | None, typer.Option("--with-docker/--without-docker", help="Include Docker files.")
    ] = None,
    provider: Annotated[str | None, typer.Option(help="openai, groq, ollama, or none (AI templates).")] = None,
    vector_store: Annotated[
        str | None, typer.Option("--vector-store", help="chroma, faiss, pgvector, or none (RAG).")
    ] = None,
    include_api: Annotated[
        bool | None, typer.Option("--with-api/--without-api", help="Include a FastAPI endpoint (RAG).")
    ] = None,
    guidance: Annotated[
        str | None, typer.Option("--guidance", help="Guidance level: learning, standard, or minimal.")
    ] = None,
    run_setup: Annotated[
        bool | None,
        typer.Option("--setup/--no-setup", help="Create the environment, install dependencies, and verify."),
    ] = None,
    no_interactive: Annotated[
        bool, typer.Option("--no-interactive", help="Never prompt; use conventional defaults.")
    ] = False,
    output: Annotated[Path | None, typer.Option("--output", "-o", help="Exact destination path.")] = None,
) -> None:
    """Create a project from a registered template.

    Template IDs: `fastapi`, `rag`, `agent`, `langgraph`, `ml`,
    `data-science`, and `cli`.
    """
    setup_result: SetupResult | None = None
    try:
        config = _resolve_config(
            project_name,
            template,
            python_version,
            package_manager,
            include_tests,
            include_docker,
            provider,
            vector_store,
            include_api,
            guidance,
            run_setup,
            no_interactive,
            output,
        )
        console.print(Panel.fit("[bold]Python Project Generator[/bold]", border_style="cyan"))
        spec = generate(config, registry)
        if config.setup:
            console.print("[cyan]Setting up the environment and verifying the starter...[/cyan]")
            setup_result = setup_project(config)
    except SetupError as exc:
        error_console.print("[yellow]Project generated, but automatic setup did not finish.[/yellow]")
        error_console.print(f"Your project is preserved at: {config.destination}")
        error_console.print(f"Failed command: {exc.command}")
        error_console.print(f"Reason: {exc}")
        error_console.print(f"From that directory, fix the reported issue and rerun: {exc.command}")
        raise typer.Exit(1) from exc
    except (InvalidProjectName, DestinationError, TemplateError, OSError) as exc:
        error_console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except (KeyboardInterrupt, EOFError, typer.Abort) as exc:
        error_console.print("\n[yellow]Cancelled; no project was changed.[/yellow]")
        raise typer.Exit(130) from exc
    except typer.BadParameter:
        raise
    except Exception as exc:
        error_console.print(f"[red]Generation failed unexpectedly:[/red] {exc}")
        raise typer.Exit(1) from exc

    if config.guidance is not Guidance.MINIMAL:
        console.print("[green]OK[/green] Created project structure")
        console.print("[green]OK[/green] Generated pyproject.toml and starter application")
        if config.include_tests:
            console.print("[green]OK[/green] Generated tests")
        if setup_result:
            console.print("[green]OK[/green] Installed dependencies and verified the starter")
        console.print("[green]OK[/green] Generated project guidance")
    console.print(f"\n[bold green]Project created successfully:[/bold green] {config.destination}")
    console.print("[bold]You're ready to build.[/bold]")
    console.print("\n[bold]Next:[/bold]")
    console.print(f'  cd "{config.destination}"')
    activation = ".\\.venv\\Scripts\\Activate.ps1" if os.name == "nt" else "source .venv/bin/activate"
    if not setup_result:
        if config.package_manager is PackageManager.UV:
            extra = " --extra dev" if config.include_tests else ""
            console.print(f"  uv sync{extra}")
        else:
            console.print("  python -m venv .venv")
            console.print(f"  {activation}")
            install_target = '".[dev]"' if config.include_tests else "."
            console.print(f"  python -m pip install -e {install_target}", markup=False)
    elif config.package_manager is PackageManager.PIP:
        console.print(f"  {activation}")
    env_template = next(
        (item for item in spec.files if item.path == ".env.example" and str(item.content).strip()),
        None,
    )
    if env_template and not setup_result:
        copy_command = "Copy-Item .env.example .env" if os.name == "nt" else "cp .env.example .env"
        console.print(f"  {copy_command}")
    elif env_template:
        console.print("  Add the required values to .env")
    if config.guidance is Guidance.LEARNING:
        console.print("  Read PROJECT_GUIDE.md for the architecture and execution flow")
    if spec.start_files:
        console.print("\n[bold]Start building in:[/bold]")
        for path in spec.start_files:
            console.print(f"  {path}")
    console.print("\n[bold]Run:[/bold]")
    for command in spec.next_commands:
        prefix = "uv run " if config.package_manager is PackageManager.UV else ""
        console.print(f"  {prefix}{command}")
