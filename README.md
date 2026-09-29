# ForgePy

> From idea to business logic.

ForgePy is a deterministic project generator for modern Python applications. It prepares the project structure, direct dependencies, configuration, starter implementation, tests, and practical guidance so you can start writing application-specific logic sooner.

Instead of repeatedly deciding where code belongs and rebuilding the same setup, run:

```console
forgepy create
```

An interactive session guides the choices:

```text
? Project name: my-api
? Project type:
> FastAPI Backend - A structured HTTP API
  RAG Application - Retrieval-augmented generation pipeline
  AI Agent - A small tool-using agent
  LangGraph Agent - An explicit state graph
  Machine Learning - A reproducible model training layout
  Data Science - An analysis and notebook workspace
  Python CLI - An installable Typer command
```

ForgePy itself does not use an LLM to generate projects. Generation is local, repeatable, and template-driven: **no AI prompts, no tokens, and no randomly generated architecture**. A generated AI application may still need the credentials or local service required by the provider you select.

## Why ForgePy?

```text
Without ForgePy
Choose a structure -> find dependencies -> configure the environment
-> initialize the framework -> add tests -> write boilerplate -> start building

With ForgePy
forgepy create -> choose what you are building
-> receive a working foundation -> start writing your logic
```

ForgePy encodes established project patterns once so your time goes toward business logic, domain rules, and application-specific behavior.

## What ForgePy handles

Depending on the selected template and options, ForgePy creates:

- a purposeful project and package structure;
- a `pyproject.toml` with only the selected direct dependencies;
- starter code that runs before you replace it with your own behavior;
- pytest tests by default;
- `.gitignore` and, when needed, a safe `.env.example`;
- a project-specific README with setup and extension steps;
- `PROJECT_GUIDE.md` in Learning mode;
- optional `Dockerfile` and `.dockerignore` files through `--with-docker`;
- pip or uv setup instructions; and
- optional environment creation, dependency installation, compilation, and tests through `--setup`.

Generation is staged before files are committed to the destination. ForgePy refuses files, symbolic links, and non-empty directories rather than overwriting existing work.

## Supported project types

| Project | Template ID | ForgePy prepares |
|---|---|---|
| FastAPI Backend | `fastapi` | Application settings, schemas, services, health and item routes, and API tests |
| RAG Application | `rag` | Document loading, chunking, retrieval, prompts, provider/vector-store wiring, and an optional API |
| AI Agent | `agent` | Tools, prompts, provider configuration, and an explicit native tool-calling loop |
| LangGraph Agent | `langgraph` | Typed state, nodes, tools, explicit edges, a compiled graph, and tests |
| Machine Learning | `ml` | Data loading, preprocessing, training, evaluation, and model persistence |
| Data Science | `data-science` | Raw/processed data layout, reusable analysis code, notebooks, figures, and tests |
| Python CLI | `cli` | An installable Typer application, console entry point, example command, and tests |

## Installation

Python 3.11 or newer is required. ForgePy is currently distributed directly through GitHub:

```console
python -m venv .venv
```

Activate the environment for your platform:

```powershell
# Windows PowerShell
.\.venv\Scripts\Activate.ps1
```

```bash
# macOS/Linux
source .venv/bin/activate
```

Install and verify ForgePy:

```console
python -m pip install "git+https://github.com/CodeCatalystHadeed/forgepy.git@main"
forgepy --version
forgepy --help
```

PyPI distribution may be added later; it is not the current installation source.

## Quick start

Start the interactive creator:

```console
forgepy create
```

A typical FastAPI session asks for the project name, Python version, package manager, guidance level, tests, Docker support, and optional setup. When generation completes, the CLI reports the created foundation and where to begin:

```text
OK Created project structure
OK Generated pyproject.toml and starter application
OK Generated tests
OK Generated project guidance

Project created successfully: <current-directory>/my-api
You're ready to build.

Start building in:
  app/services/items.py
  app/schemas/items.py
  app/api/routes/items.py
```

The generated README contains the exact setup and run commands for that project. For the default pip-based FastAPI starter:

```console
cd my-api
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

The generated README shows these platform-specific activation commands as part of its setup path.

## Guidance levels

Guidance changes the documentation, not the application architecture or project quality.

| Level | Intended experience |
|---|---|
| `learning` | Adds `PROJECT_GUIDE.md` with native framework terms, execution flow, extension points, and a learning loop |
| `standard` | Provides practical setup, architecture, important files, and recommended next steps |
| `minimal` | Keeps the generated README focused on setup, starting points, environment values, and run commands |

Select a level interactively or pass it explicitly:

```console
forgepy create my-api --template fastapi --guidance minimal --no-interactive
```

## Example: FastAPI

A Learning-mode FastAPI project includes this working foundation:

```text
my-api/
|-- app/
|   |-- main.py
|   |-- api/routes/
|   |   |-- health.py
|   |   `-- items.py
|   |-- core/config.py
|   |-- schemas/items.py
|   `-- services/items.py
|-- tests/test_health.py
|-- .env.example
|-- .gitignore
|-- pyproject.toml
|-- README.md
`-- PROJECT_GUIDE.md
```

- `schemas/` defines and validates request/response data.
- `services/` is the seam for business and domain logic.
- `api/routes/` maps HTTP requests to services.
- `core/` owns application configuration.

```text
Request -> Route -> Pydantic validation -> Service -> Business logic -> Response
```

The starter includes `/health` and an in-memory `/items` example so it is runnable while leaving clear places for your own persistence and domain behavior.

## Example: RAG

RAG choices compose independently. For example:

```text
RAG + Groq + Chroma + FastAPI
```

Create that combination non-interactively:

```console
forgepy create knowledge-api --template rag --provider groq --vector-store chroma --with-api --guidance learning --no-interactive
```

ForgePy composes the matching dependencies, `GROQ_API_KEY` example, model and vector-store adapters, ingestion/retrieval pipeline, API endpoints, tests, and guidance.

```text
Documents -> Loader -> Chunking -> Embeddings -> Vector store
-> Retrieval -> Prompt -> Model -> Answer
```

The generated Chroma, FAISS, and pgvector adapters use deterministic hashing embeddings to make the integration runnable and testable. They demonstrate wiring, not production-quality semantic retrieval; replace `_embed` in `app/config/vector_store.py` with an embedding model suited to your data.

### Providers and vector stores

| Choice | CLI value | Notes |
|---|---|---|
| OpenAI | `openai` | Adds OpenAI/LangChain integration and `OPENAI_API_KEY` |
| Groq | `groq` | Adds Groq/LangChain integration and `GROQ_API_KEY` |
| Ollama | `ollama` | Adds the Ollama integration and a local base URL setting |
| Configure later | `none` | Keeps the provider seam without requiring model credentials |

| Choice | CLI value | Notes |
|---|---|---|
| Chroma | `chroma` | Persistent local Chroma collection |
| FAISS | `faiss` | In-process FAISS index |
| pgvector | `pgvector` | PostgreSQL/pgvector adapter using `DATABASE_URL` |
| No external store | `none` | Small in-memory keyword-ranked starter |

Provider choices apply to RAG, AI Agent, and LangGraph templates. Vector-store and `--with-api` choices apply to RAG. ForgePy adds only the direct dependencies required by the selected combination.

## Generate only or generate and set up

By default, ForgePy generates the project and prints the commands you can run later:

```console
forgepy create my-api --template fastapi --no-setup --no-interactive
```

With `--setup`, ForgePy also prepares the selected package-manager workflow:

```console
forgepy create my-api --template fastapi --setup --no-interactive
```

For pip, setup creates `.venv` and installs the generated project. For uv, it runs `uv sync`. ForgePy then compiles the generated `app/` or `src/` package and runs tests when tests were selected. If `.env.example` exists, setup copies it to an untracked `.env` without filling secret values.

Generation itself does not contact package indexes. Dependency installation may require internet access unless the packages are already cached. If setup fails, the generated project is preserved and the CLI prints the exact command to retry.

## pip and uv workflows

Choose either workflow during generation:

```console
forgepy create pip-api --template fastapi --package-manager pip --no-interactive
forgepy create uv-api --template fastapi --package-manager uv --no-interactive
```

Generated pip projects use a standard virtual environment and editable install:

```console
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
pytest
```

Generated uv projects use:

```console
uv sync --extra dev
uv run pytest
```

## Learning without lock-in

ForgePy is the builder, not the framework. Generated projects use normal ecosystem tools such as FastAPI, Pydantic, LangGraph, LangChain integrations, Typer, pytest, scikit-learn, pandas, and JupyterLab.

The generated application does not depend on ForgePy at runtime. You can generate a project, remove ForgePy, and continue with the underlying tools and conventions directly.

## Offline generation

Once ForgePy is installed, project generation is local and works without a network connection. Installing generated dependencies can require network access, and applications configured for hosted model providers require access to those providers. Offline generation does not imply that every generated application runs offline.

## Non-interactive usage

All required choices can be passed as flags for repeatable setup:

```console
forgepy create payments-api --template fastapi --package-manager uv --guidance minimal --no-interactive
```

This is useful for experienced developers, scripts, workshops, tutorials, and other repeatable workflows. Run `forgepy create --help` for every supported option. Generated projects can target Python 3.11 or 3.12 through `--python`.

## Project philosophy

ForgePy aims to:

- automate repetitive setup;
- expose real framework concepts;
- follow native ecosystem conventions;
- provide useful, deterministic defaults; and
- get out of the way once generation is complete.

It is not an AI code generator, a runtime framework, or an abstraction layer that hides the generated framework.

## Development

Clone the repository and create a development environment:

```console
git clone https://github.com/CodeCatalystHadeed/forgepy.git
cd forgepy
python -m venv .venv
```

Activate the environment, then install and run the checks:

```console
python -m pip install -e ".[dev]"
python -m pytest
python -m ruff check .
python -m ruff format --check .
python -m build
```

## Contributing

Contributions are welcome. Bug fixes, documentation improvements, template refinements, compatibility fixes, and focused tests are especially useful. Read [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request.

## Security

Please follow [SECURITY.md](SECURITY.md) to report a vulnerability privately. Do not disclose suspected vulnerabilities in a public issue.

## License

ForgePy is available under the [MIT License](LICENSE).
