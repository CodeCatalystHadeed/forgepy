"""Shared, deliberately small helpers used by built-in templates."""

from collections.abc import Iterable

from forgepy.config import Guidance, PackageManager, ProjectConfig, Provider, VectorStore
from forgepy.models import ProjectFile

COMMON_GITIGNORE = """__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/
.ruff_cache/
.env
build/
dist/
"""

PROVIDER_DEPENDENCIES = {
    Provider.OPENAI: ("langchain-openai", "openai", "python-dotenv"),
    Provider.GROQ: ("groq", "langchain-groq", "python-dotenv"),
    Provider.OLLAMA: ("langchain-ollama", "python-dotenv"),
    Provider.NONE: (),
}
VECTOR_DEPENDENCIES = {
    VectorStore.CHROMA: ("chromadb",),
    VectorStore.FAISS: ("faiss-cpu", "numpy"),
    VectorStore.PGVECTOR: ("pgvector", "psycopg[binary]"),
    VectorStore.NONE: (),
}


def dependencies(*groups: Iterable[str]) -> tuple[str, ...]:
    """Compose dependency groups without duplicates and with stable ordering."""
    return tuple(sorted({dependency for group in groups for dependency in group}, key=str.lower))


def project_toml(
    config: ProjectConfig,
    runtime: Iterable[str],
    *,
    script: tuple[str, str] | None = None,
    package_path: str = "app",
) -> str:
    deps = dependencies(runtime)
    dep_lines = "\n".join(f'  "{item}",' for item in deps)
    dev_dependencies = ["pytest>=8"]
    if config.template_id == "fastapi" or config.include_api:
        dev_dependencies.append("httpx2")
    dev_lines = ", ".join(f'"{item}"' for item in dev_dependencies)
    script_block = ""
    if script:
        script_block = f'\n[project.scripts]\n"{script[0]}" = "{script[1]}"\n'
    pytest_path = "src" if package_path.startswith("src/") else "."
    return f'''[build-system]
requires = ["hatchling>=1.25"]
build-backend = "hatchling.build"

[project]
name = "{config.project_name}"
version = "0.1.0"
description = "Generated with ForgePy"
readme = "README.md"
requires-python = ">={config.python_version}"
dependencies = [
{dep_lines}
]
{script_block}
[project.optional-dependencies]
dev = [{dev_lines}]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["{pytest_path}"]

[tool.hatch.build.targets.wheel]
packages = ["{package_path}"]
'''


def install_section(config: ProjectConfig) -> str:
    if config.package_manager is PackageManager.UV:
        command = "uv sync --extra dev" if config.include_tests else "uv sync"
        return f"""```console
{command}
```"""
    install_target = '".[dev]"' if config.include_tests else "."
    return f"""```console
python -m venv .venv
# Windows PowerShell: .\\.venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e {install_target}
```"""


def readme(
    config: ProjectConfig,
    *,
    template_name: str,
    summary: str,
    tree: str,
    run: str,
    architecture: str,
    important: str,
    start_here: tuple[str, ...] = (),
    environment: str | None = None,
    docker_port: int | None = None,
) -> str:
    test_text = (
        "Run `pytest` from the project root."
        if config.include_tests
        else "Tests were not selected; add a `tests/` directory and pytest when ready."
    )
    environment_section = ""
    if environment is not None:
        environment_section = f"""## Environment variables

{environment}

Never commit `.env`; `.env.example` is safe to commit.

"""
    docker_section = ""
    if config.include_docker:
        port = f" -p {docker_port}:{docker_port}" if docker_port else ""
        docker_section = f"""## Docker

```console
docker build -t {config.project_name} .
docker run --rm{port} {config.project_name}
```

"""
    start_section = ""
    if start_here:
        steps = "\n".join(f"{index}. {step}" for index, step in enumerate(start_here, start=1))
        start_section = f"""## Start here

{steps}

"""
    if config.guidance is Guidance.MINIMAL:
        environment_minimal = environment_section if environment is not None else ""
        return f"""# {config.project_name}

{summary}

{start_section}## Setup

{install_section(config)}

{environment_minimal}## Run

```console
{run}
```
"""
    guide_note = (
        "See `PROJECT_GUIDE.md` for the architecture, terminology, and execution flow.\n\n"
        if config.guidance is Guidance.LEARNING
        else ""
    )
    return f"""# {config.project_name}

{summary}

Generated from ForgePy's **{template_name}** template.

{guide_note}
{start_section}
## Project structure

```text
{tree}
```

## Requirements and setup

Python {config.python_version} or newer is required.

{install_section(config)}

{environment_section}
## Run

```console
{run}
```

## Tests

{test_text}

{docker_section}
## Architecture

{architecture}

## Important files

{important}

## Recommended next steps

Replace the starter behavior with domain logic, add focused tests, enable linting and type checking, then configure CI before deployment.
"""


_GUIDES: dict[str, tuple[str, str, tuple[str, ...], tuple[str, ...], tuple[str, ...]]] = {
    "fastapi": (
        "FastAPI Backend",
        "Request -> Route -> Pydantic validation -> Service -> Business logic -> Response",
        (
            "Route: maps an HTTP method and URL to a Python function.",
            "Schema: validates incoming data and documents outgoing data.",
            "Service: holds application behavior independently of HTTP.",
        ),
        ("app/schemas/items.py", "app/services/items.py", "app/api/routes/items.py"),
        ("app/main.py", "app/core/config.py"),
    ),
    "rag": (
        "RAG Application",
        "Document -> Loader -> Chunking -> Embedding -> Vector store -> Retrieval -> Prompt -> LLM -> Answer",
        (
            "Chunk: a small document segment stored for retrieval.",
            "Vector store: indexes chunks and returns relevant context.",
            "Embedding: the starter uses deterministic hashing for local wiring and tests; use a semantic model for production retrieval quality.",
            "Prompt: combines retrieved context with the user's question.",
        ),
        ("app/loaders/documents.py", "app/rag/ingestion.py", "app/rag/prompts.py", "app/rag/pipeline.py"),
        ("app/config/provider.py", "app/config/vector_store.py"),
    ),
    "agent": (
        "AI Agent",
        "User message -> Model -> Tool choice -> Tool result -> Model -> Answer",
        (
            "Tool: a typed capability the model may choose to call.",
            "Instruction: defines the agent's role and boundaries.",
            "Tool loop: returns tool results to the model until it answers.",
        ),
        ("app/agent/tools.py", "app/agent/prompts.py", "app/agent/agent.py"),
        ("app/config/provider.py",),
    ),
    "langgraph": (
        "LangGraph Agent",
        "Input -> State -> Node -> Edge -> Node -> Output",
        (
            "State: the typed data carried through the workflow.",
            "Node: a function that reads and updates state.",
            "Edge: an explicit transition between nodes.",
        ),
        ("app/graph/state.py", "app/graph/nodes.py", "app/graph/graph.py"),
        ("app/config/provider.py",),
    ),
    "ml": (
        "Machine Learning",
        "Raw data -> Load -> Feature pipeline -> Train/test split -> Model -> Evaluation -> Saved artifact",
        (
            "Feature pipeline: preprocessing fitted only from training data.",
            "Estimator: the algorithm that learns from prepared features.",
            "Artifact: the persisted pipeline used later for prediction.",
        ),
        ("src/{package}/data/load.py", "src/{package}/features/build.py", "src/{package}/models/train.py"),
        ("pyproject.toml",),
    ),
    "data-science": (
        "Data Science",
        "Raw data -> Load -> Explore -> Reusable analysis -> Processed data -> Figures",
        (
            "Raw data: immutable source input.",
            "Notebook: exploratory work and communication.",
            "Analysis module: reusable logic that should not be duplicated across notebooks.",
        ),
        ("src/{package}/io.py", "src/{package}/analysis.py", "notebooks/"),
        ("pyproject.toml",),
    ),
    "cli": (
        "Python CLI",
        "Shell arguments -> Typer validation -> Command -> Business logic -> Terminal output",
        (
            "Command: a typed Python function exposed at the terminal.",
            "Option: a named input such as `--format json`.",
            "Console script: the installed command declared in `pyproject.toml`.",
        ),
        ("src/{package}/cli.py", "tests/test_cli.py"),
        ("pyproject.toml",),
    ),
}


def guidance_files(config: ProjectConfig) -> list[ProjectFile]:
    """Return learning-only documentation without changing application architecture."""
    if config.guidance is not Guidance.LEARNING:
        return []
    title, flow, concepts, edit_first, foundations = _GUIDES[config.template_id]
    package = config.package_name
    edit_lines = "\n".join(f"- `{path.format(package=package)}`" for path in edit_first)
    foundation_lines = "\n".join(f"- `{path.format(package=package)}`" for path in foundations)
    concept_lines = "\n".join(f"- {concept}" for concept in concepts)
    return [
        ProjectFile(
            "PROJECT_GUIDE.md",
            f"""# {title}: project guide

This guide explains the native Python ecosystem used by this starter. ForgePy is not required to run it.

## Execution flow

```text
{flow}
```

## Key terms

{concept_lines}

## Edit these first

{edit_lines}

These are the extension points for your application-specific behavior. Follow the numbered `Start here` section in `README.md` for the first working change.

## Leave these alone initially

{foundation_lines}

These files contain working setup or integration wiring. Read them to learn how the project connects, but change them only when your requirements differ.

## Learning loop

1. Run the starter and its tests unchanged.
2. Make one small application-specific change in an **Edit these first** file.
3. Add or update a test that demonstrates the behavior.
4. Run the project again and follow the data through the execution flow above.
""",
        )
    ]


def standard_files(
    config: ProjectConfig,
    *,
    extra_ignore: str = "",
    docker_command: str = "python -m app.main",
    docker_port: int | None = None,
) -> list[ProjectFile]:
    files = [ProjectFile(".gitignore", COMMON_GITIGNORE + extra_ignore)]
    if config.include_docker:
        files.extend(
            [
                ProjectFile(
                    "Dockerfile",
                    f'''FROM python:{config.python_version}-slim
WORKDIR /app
COPY . .
RUN python -m pip install --no-cache-dir .
{f"EXPOSE {docker_port}" if docker_port else ""}
CMD ["sh", "-c", "{docker_command}"]
''',
                ),
                ProjectFile(".dockerignore", ".git\n.venv\n__pycache__\n*.pyc\n.pytest_cache\n.env\n"),
            ]
        )
    return files


def env_file(config: ProjectConfig, *, extra: Iterable[str] = ()) -> ProjectFile:
    variables: list[str] = []
    if config.provider is Provider.OPENAI:
        variables.append("OPENAI_API_KEY=")
    elif config.provider is Provider.GROQ:
        variables.append("GROQ_API_KEY=")
    elif config.provider is Provider.OLLAMA:
        variables.append("OLLAMA_BASE_URL=http://localhost:11434")
    if config.vector_store is VectorStore.PGVECTOR:
        variables.append("DATABASE_URL=")
    variables.extend(extra)
    return ProjectFile(".env.example", "\n".join(variables) + ("\n" if variables else ""))


def provider_dependencies(config: ProjectConfig) -> tuple[str, ...]:
    return PROVIDER_DEPENDENCIES[config.provider]


def vector_dependencies(config: ProjectConfig) -> tuple[str, ...]:
    return VECTOR_DEPENDENCIES[config.vector_store]


def init_files(*directories: str) -> list[ProjectFile]:
    return [ProjectFile(f"{directory}/__init__.py", "") for directory in directories]
