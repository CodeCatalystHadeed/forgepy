import py_compile
import tomllib
from pathlib import Path

import pytest

from forgepy.config import Guidance, PackageManager, ProjectConfig, Provider, VectorStore
from forgepy.generator import build_spec, generate
from forgepy.registry import registry
from forgepy.utils.filesystem import DestinationError


def config(tmp_path: Path, template: str, **overrides) -> ProjectConfig:
    values = dict(
        project_name="sample-project",
        package_name="sample_project",
        destination=tmp_path / template,
        template_id=template,
        python_version="3.12",
        package_manager=PackageManager.PIP,
        include_tests=True,
        include_docker=False,
        provider=Provider.NONE,
        vector_store=VectorStore.NONE,
        include_api=False,
    )
    values.update(overrides)
    return ProjectConfig(**values)


@pytest.mark.parametrize(
    ("template", "expected"),
    [
        ("fastapi", "app/api/routes/health.py"),
        ("rag", "app/rag/pipeline.py"),
        ("agent", "app/agent/tools.py"),
        ("langgraph", "app/graph/graph.py"),
        ("ml", "src/sample_project/models/train.py"),
        ("data-science", "src/sample_project/analysis.py"),
        ("cli", "src/sample_project/cli.py"),
    ],
)
def test_every_template_generates_valid_project(tmp_path: Path, template: str, expected: str) -> None:
    cfg = config(tmp_path, template)
    generate(cfg, registry)
    root = cfg.destination
    assert (root / expected).is_file()
    assert (root / "README.md").read_text(encoding="utf-8").startswith("# sample-project")
    assert "## Start here" in (root / "README.md").read_text(encoding="utf-8")
    assert ".env\n" in (root / ".gitignore").read_text(encoding="utf-8")
    with (root / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)
    assert metadata["project"]["name"] == "sample-project"
    assert metadata["project"]["requires-python"] == ">=3.12"
    assert not any(dependency.lower().startswith("forgepy") for dependency in metadata["project"]["dependencies"])
    for source in root.rglob("*.py"):
        py_compile.compile(str(source), doraise=True)


@pytest.mark.parametrize("template", ["fastapi", "rag", "agent", "langgraph", "ml", "data-science", "cli"])
def test_guidance_levels_change_docs_not_application_architecture(tmp_path: Path, template: str) -> None:
    generated: dict[Guidance, Path] = {}
    for guidance in Guidance:
        cfg = config(tmp_path, template, destination=tmp_path / f"{template}-{guidance}", guidance=guidance)
        generate(cfg, registry)
        generated[guidance] = cfg.destination

    learning = generated[Guidance.LEARNING]
    standard = generated[Guidance.STANDARD]
    minimal = generated[Guidance.MINIMAL]
    assert (learning / "PROJECT_GUIDE.md").is_file()
    assert not (standard / "PROJECT_GUIDE.md").exists()
    assert not (minimal / "PROJECT_GUIDE.md").exists()
    assert "## Execution flow" in (learning / "PROJECT_GUIDE.md").read_text()
    assert "## Architecture" in (standard / "README.md").read_text()
    assert "## Architecture" not in (minimal / "README.md").read_text()
    assert "## Start here" in (minimal / "README.md").read_text()

    def application_files(root: Path) -> dict[str, bytes]:
        return {
            path.relative_to(root).as_posix(): path.read_bytes()
            for path in root.rglob("*")
            if path.is_file() and path.name not in {"README.md", "PROJECT_GUIDE.md"}
        }

    assert application_files(learning) == application_files(standard) == application_files(minimal)


def test_all_rag_provider_store_combinations_are_composed_without_lock_in(tmp_path: Path) -> None:
    provider_packages = {
        Provider.OPENAI: {"langchain-openai", "openai", "python-dotenv"},
        Provider.GROQ: {"groq", "langchain-groq", "python-dotenv"},
        Provider.OLLAMA: {"langchain-ollama", "python-dotenv"},
        Provider.NONE: set(),
    }
    store_packages = {
        VectorStore.CHROMA: {"chromadb"},
        VectorStore.FAISS: {"faiss-cpu", "numpy"},
        VectorStore.PGVECTOR: {"pgvector", "psycopg[binary]"},
        VectorStore.NONE: set(),
    }
    selectable = set().union(*provider_packages.values(), *store_packages.values())
    for provider, expected_provider in provider_packages.items():
        for store, expected_store in store_packages.items():
            cfg = config(tmp_path, "rag", provider=provider, vector_store=store)
            spec = build_spec(cfg, registry)
            expected = expected_provider | expected_store
            if store is VectorStore.PGVECTOR:
                expected.add("python-dotenv")
            assert set(spec.dependencies) & selectable == expected
            assert not any(dependency.lower().startswith("forgepy") for dependency in spec.dependencies)


def test_rag_feature_dependencies_are_exact(tmp_path: Path) -> None:
    cfg = config(tmp_path, "rag", provider=Provider.OPENAI, vector_store=VectorStore.CHROMA, include_api=True)
    spec = build_spec(cfg, registry)
    assert {"openai", "langchain-openai", "chromadb", "fastapi", "uvicorn[standard]"} <= set(spec.dependencies)
    assert not {"groq", "langchain-groq", "langchain-ollama", "faiss-cpu", "pgvector"} & set(spec.dependencies)
    assert len(spec.dependencies) == len(set(spec.dependencies))
    generate(cfg, registry)
    assert (cfg.destination / "app/api.py").exists()
    env = (cfg.destination / ".env.example").read_text()
    assert "OPENAI_API_KEY=" in env
    assert "GROQ_API_KEY" not in env


def test_rag_without_api_does_not_generate_api(tmp_path: Path) -> None:
    cfg = config(tmp_path, "rag")
    generate(cfg, registry)
    assert not (cfg.destination / "app/api.py").exists()


def test_rag_pipeline_uses_selected_integrations(tmp_path: Path) -> None:
    cfg = config(tmp_path, "rag", provider=Provider.GROQ, vector_store=VectorStore.CHROMA, include_api=True)
    generate(cfg, registry)
    pipeline = (cfg.destination / "app/rag/pipeline.py").read_text()
    api = (cfg.destination / "app/api.py").read_text()
    vector_store = (cfg.destination / "app/config/vector_store.py").read_text()
    assert "create_vector_store()" in pipeline
    assert "create_chat_model().invoke(prompt)" in pipeline
    assert "load_document(path)" in pipeline
    assert '@app.post("/documents"' in api
    assert '@app.post("/query")' in api
    assert "query_embeddings=[_embed(query)]" in vector_store
    assert "query_texts" not in vector_store


def test_agent_uses_native_model_tool_calls(tmp_path: Path) -> None:
    cfg = config(tmp_path, "agent", provider=Provider.OPENAI)
    generate(cfg, registry)
    agent = (cfg.destination / "app/agent/agent.py").read_text()
    tools = (cfg.destination / "app/agent/tools.py").read_text()
    assert "create_chat_model().bind_tools(TOOLS)" in agent
    assert "response.tool_calls" in agent
    assert "ToolMessage" in agent
    assert "@tool" in tools
    assert "message.startswith" not in agent


def test_fastapi_starter_points_to_business_logic(tmp_path: Path) -> None:
    cfg = config(tmp_path, "fastapi")
    spec = build_spec(cfg, registry)
    generate(cfg, registry)
    assert spec.start_files == ("app/services/items.py", "app/schemas/items.py", "app/api/routes/items.py")
    assert (cfg.destination / "app/services/items.py").is_file()
    assert (cfg.destination / "app/schemas/items.py").is_file()
    assert "HTTPException" in (cfg.destination / "app/api/routes/items.py").read_text()
    with (cfg.destination / "pyproject.toml").open("rb") as handle:
        metadata = tomllib.load(handle)
    assert "httpx2" in metadata["project"]["optional-dependencies"]["dev"]


def test_rag_api_adds_test_client_dependency_only_with_api(tmp_path: Path) -> None:
    for include_api in (False, True):
        cfg = config(tmp_path, "rag", destination=tmp_path / f"rag-{include_api}", include_api=include_api)
        generate(cfg, registry)
        with (cfg.destination / "pyproject.toml").open("rb") as handle:
            metadata = tomllib.load(handle)
        assert ("httpx2" in metadata["project"]["optional-dependencies"]["dev"]) is include_api


def test_ml_starter_loads_features_and_persists_a_model(tmp_path: Path) -> None:
    cfg = config(tmp_path, "ml")
    generate(cfg, registry)
    train = (cfg.destination / "src/sample_project/models/train.py").read_text()
    assert "load_dataset" in train
    assert "build_preprocessor" in train
    assert "joblib.dump" in train


def test_tests_and_docker_options(tmp_path: Path) -> None:
    cfg = config(tmp_path, "fastapi", include_tests=False, include_docker=True)
    generate(cfg, registry)
    assert not (cfg.destination / "tests").exists()
    assert (cfg.destination / "Dockerfile").exists()
    assert "uvicorn app.main:app" in (cfg.destination / "Dockerfile").read_text()


def test_uv_readme_does_not_instruct_pip_install(tmp_path: Path) -> None:
    cfg = config(tmp_path, "agent", package_manager=PackageManager.UV)
    generate(cfg, registry)
    readme_text = (cfg.destination / "README.md").read_text()
    assert "uv sync --extra dev" in readme_text
    assert "pip install" not in readme_text


def test_existing_nonempty_directory_is_untouched(tmp_path: Path) -> None:
    destination = tmp_path / "existing"
    destination.mkdir()
    marker = destination / "keep.txt"
    marker.write_text("mine")
    cfg = config(tmp_path, "fastapi", destination=destination)
    with pytest.raises(DestinationError, match="not empty"):
        generate(cfg, registry)
    assert marker.read_text() == "mine"
    assert list(destination.iterdir()) == [marker]


def test_destination_file_is_rejected(tmp_path: Path) -> None:
    destination = tmp_path / "file"
    destination.write_text("mine")
    with pytest.raises(DestinationError, match="is a file"):
        generate(config(tmp_path, "cli", destination=destination), registry)
    assert destination.read_text() == "mine"


def test_existing_empty_directory_is_supported(tmp_path: Path) -> None:
    destination = tmp_path / "empty"
    destination.mkdir()
    generate(config(tmp_path, "cli", destination=destination), registry)
    assert (destination / "pyproject.toml").exists()


def test_failed_commit_leaves_existing_empty_directory_empty(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "empty"
    destination.mkdir()

    def fail_replace(source, target):
        raise PermissionError("simulated read-only destination")

    monkeypatch.setattr("forgepy.utils.filesystem.os.replace", fail_replace)
    with pytest.raises(PermissionError, match="read-only"):
        generate(config(tmp_path, "fastapi", destination=destination), registry)
    assert destination.is_dir()
    assert not list(destination.iterdir())


def test_symlink_destination_is_rejected(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "link"
    monkeypatch.setattr(Path, "is_symlink", lambda path: path == destination)
    with pytest.raises(DestinationError, match="symbolic link"):
        generate(config(tmp_path, "cli", destination=destination), registry)


def test_concurrent_destination_is_never_deleted(tmp_path: Path, monkeypatch) -> None:
    destination = tmp_path / "raced"
    original_write_text = Path.write_text

    def fail_after_external_create(path, *args, **kwargs):
        destination.mkdir()
        original_write_text(destination / "someone-elses-file.txt", "keep")
        raise PermissionError("simulated staging failure")

    monkeypatch.setattr(Path, "write_text", fail_after_external_create)
    with pytest.raises(PermissionError, match="staging"):
        generate(config(tmp_path, "fastapi", destination=destination), registry)
    assert (destination / "someone-elses-file.txt").read_text() == "keep"


@pytest.mark.parametrize(
    ("provider", "included", "excluded", "variable"),
    [
        (Provider.OPENAI, "langchain-openai", "langchain-groq", "OPENAI_API_KEY="),
        (Provider.GROQ, "langchain-groq", "langchain-openai", "GROQ_API_KEY="),
        (Provider.OLLAMA, "langchain-ollama", "langchain-openai", "OLLAMA_BASE_URL="),
        (Provider.NONE, None, "langchain-openai", None),
    ],
)
def test_rag_provider_matrix(tmp_path: Path, provider, included, excluded, variable) -> None:
    cfg = config(tmp_path, "rag", provider=provider)
    spec = build_spec(cfg, registry)
    if included:
        assert included in spec.dependencies
    assert excluded not in spec.dependencies
    generate(cfg, registry)
    provider_source = (cfg.destination / "app/config/provider.py").read_text()
    env_path = cfg.destination / ".env.example"
    if included:
        assert included.replace("-", "_") in provider_source or provider is Provider.OLLAMA
    if variable:
        assert variable in env_path.read_text()
    else:
        assert not env_path.exists()


@pytest.mark.parametrize(
    ("store", "expected"),
    [
        (VectorStore.CHROMA, {"chromadb"}),
        (VectorStore.FAISS, {"faiss-cpu"}),
        (VectorStore.PGVECTOR, {"pgvector", "psycopg[binary]"}),
        (VectorStore.NONE, set()),
    ],
)
def test_rag_vector_store_matrix(tmp_path: Path, store, expected) -> None:
    cfg = config(tmp_path, "rag", vector_store=store)
    spec = build_spec(cfg, registry)
    all_store_dependencies = {"chromadb", "faiss-cpu", "pgvector", "psycopg[binary]"}
    assert set(spec.dependencies) & all_store_dependencies == expected
    generate(cfg, registry)
    source = (cfg.destination / "app/config/vector_store.py").read_text()
    expected_imports = {
        VectorStore.CHROMA: "import chromadb",
        VectorStore.FAISS: "import faiss",
        VectorStore.PGVECTOR: "from pgvector.psycopg import register_vector",
        VectorStore.NONE: "class VectorStore:",
    }
    assert expected_imports[store] in source


def test_fastapi_uses_validated_settings(tmp_path: Path) -> None:
    cfg = config(tmp_path, "fastapi")
    generate(cfg, registry)
    main = (cfg.destination / "app/main.py").read_text()
    assert "from app.core.config import settings" in main
    assert "FastAPI(title=settings.app_name)" in main


def test_generated_src_layout_uses_project_package(tmp_path: Path) -> None:
    for template in ("ml", "data-science", "cli"):
        cfg = config(tmp_path, template)
        generate(cfg, registry)
        metadata = tomllib.loads((cfg.destination / "pyproject.toml").read_text())
        assert metadata["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"] == ["src/sample_project"]
        assert metadata["tool"]["pytest"]["ini_options"]["pythonpath"] == ["src"]


def test_docker_readme_and_runtime_match(tmp_path: Path) -> None:
    cfg = config(tmp_path, "rag", include_api=True, include_docker=True)
    generate(cfg, registry)
    dockerfile = (cfg.destination / "Dockerfile").read_text()
    readme = (cfg.destination / "README.md").read_text()
    assert "uvicorn app.api:app --host 0.0.0.0 --port 8000" in dockerfile
    assert "EXPOSE 8000" in dockerfile
    assert "docker run --rm -p 8000:8000" in readme


def test_no_docker_instructions_when_disabled(tmp_path: Path) -> None:
    cfg = config(tmp_path, "cli", include_docker=False)
    generate(cfg, registry)
    assert "## Docker" not in (cfg.destination / "README.md").read_text()
