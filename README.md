# ForgePy

ForgePy is an open-source CLI that creates clean, runnable Python projects for backend, AI, data, machine-learning, agentic, and command-line work. It favors explicit starter code and safe filesystem behavior over a large framework.

ForgePy generates FastAPI, RAG, AI Agent, LangGraph, machine-learning, data-science, and Python CLI starters. Generation is staged before commit and refuses non-empty destinations.

> ForgePy 1.0.0 is prepared as a release candidate but has not been published from this repository.

## Installation

After a PyPI release, installation will be:

```console
python -m pip install forgepy
```

Until then, install the reviewed source directly from the public GitHub repository:

```console
python -m pip install "git+https://github.com/CodeCatalystHadeed/forgepy.git@main"
```

### Editable development installation

Python 3.11 or newer is required.

```console
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Quick start

```console
forgepy create
forgepy create my-api --template fastapi
```

For automation, disable prompts and provide the name and template:

```console
forgepy create my-rag --template rag --provider openai --vector-store chroma --with-api --package-manager uv --no-interactive
forgepy create analytics --template data-science --without-docker --no-interactive
forgepy create payments-api --template fastapi --package-manager uv --guidance minimal --no-interactive
```

Run `forgepy create --help` for all flags. ForgePy refuses non-empty destinations and never offers a destructive force mode.

## Templates

| ID | Generated project |
|---|---|
| `fastapi` | FastAPI service with `/health`, settings, and tests |
| `rag` | Loading/ingestion/retrieval/pipeline structure with provider and vector-store selection |
| `agent` | Separated prompts, tools, orchestration, and configuration |
| `langgraph` | Executable state/node/edge graph |
| `ml` | Data, features, models, notebooks, and training baseline |
| `data-science` | Analysis code, notebooks, data, reports, and figures |
| `cli` | Installable Typer app with a console-script entry point |

RAG supports OpenAI, Groq, Ollama, or deferred provider configuration; Chroma, FAISS, pgvector, or no vector store; and an optional FastAPI endpoint. Provider packages are included only when selected.

The generated Chroma, FAISS, and pgvector adapters use small deterministic hashing embeddings so the starter pipeline can be tested locally without another model download. They demonstrate integration wiring, not production-quality semantic retrieval. Replace `_embed` in `app/config/vector_store.py` with an embedding model appropriate for your documents before evaluating retrieval quality.

## Generated project example

```console
forgepy create demo-api --template fastapi --with-tests --with-docker --no-interactive
cd demo-api
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
pytest
```

Each generated project has a practical `Start here` path. Guidance defaults to `standard`; `--guidance learning` adds `PROJECT_GUIDE.md` with native-framework terminology and execution flow, while `--guidance minimal` keeps only essential setup, extension points, and run commands. Guidance never changes application architecture.

Generation itself is deterministic and offline: ForgePy writes files but does not contact package indexes. Add `--setup` to create the environment, install or sync dependencies, compile the starter, and run its tests. If installation fails, the generated project is preserved and ForgePy reports the exact command to retry. Without `--setup`, run the README's pip workflow or `uv sync --extra dev` yourself.

An interactive session asks for the project name, template, Python version, package manager, guidance level, tests, Docker, optional setup, and only the feature choices supported by the selected template. Pressing Ctrl+C during generation cancels without writing a project. Once generation finishes, a setup failure never deletes the project.

## Architecture

```text
Typer CLI + Questionary prompts
             |
      validated ProjectConfig
             |
       TemplateRegistry
             |
   builder -> ProjectSpec
             |
 transactional filesystem writer
             |
       generated project
             |
  optional native pip/uv setup
```

`src/forgepy/cli.py` owns presentation and input. `config.py` contains validated choices. `registry/templates.py` describes available templates. Builders compose dependencies and files into immutable specifications. `generator.py` is template-independent, and `utils/filesystem.py` stages the whole tree before moving it into place.

## Adding a template

Implement a builder that accepts `ProjectConfig` and returns `ProjectSpec`, then register a `Template` with its ID, name, description, capabilities, and builder. Core generation requires no modification. See [CONTRIBUTING.md](CONTRIBUTING.md) for the checklist.

## Development and testing

```console
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
python -m build
```

Tests cover the CLI, name and path safety, registry validation, dependency composition, optional files, TOML parsing, setup failure recovery, guidance modes, and compilation of Python files generated by every template.

## Release preparation

The repository CI tests Python 3.11 and 3.13 on Windows, macOS, and Linux, then builds and independently smoke-tests both the wheel and source distribution. The publish workflow uses PyPI Trusted Publishing, validates the release version, and runs only for an intentionally published GitHub Release or a manual dispatch protected by the `pypi` GitHub environment.

Before the first PyPI release, the repository owner must:

1. Enable GitHub private vulnerability reporting.
2. Create and protect a `pypi` GitHub environment.
3. Configure a matching PyPI Trusted Publisher for `.github/workflows/publish.yml`.
4. Confirm the distribution name immediately before upload; package-index names are first-come, first-served. On 2026-09-29 the exact `forgepy` PyPI project page returned 404, but this does not reserve the name. A separate published `forgepy-cli` distribution already uses the `forgepy` command, so the owner should assess that user-facing collision.

No publishing command is run by the test suite or CI workflow.

See [RELEASING.md](RELEASING.md) for the owner-only GitHub and PyPI release procedure.

## License

MIT. See [LICENSE](LICENSE).
