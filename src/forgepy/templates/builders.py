"""Registry-friendly builders for the seven built-in project types."""

from forgepy.config import ProjectConfig, Provider, VectorStore
from forgepy.models import ProjectFile, ProjectSpec
from forgepy.templates.shared import (
    dependencies,
    env_file,
    guidance_files,
    init_files,
    project_toml,
    provider_dependencies,
    readme,
    standard_files,
    vector_dependencies,
)


def _tests(config: ProjectConfig, path: str, content: str) -> list[ProjectFile]:
    return [ProjectFile("tests/__init__.py", ""), ProjectFile(path, content)] if config.include_tests else []


def _spec(
    config: ProjectConfig,
    files: list[ProjectFile],
    deps: tuple[str, ...],
    commands: tuple[str, ...],
    *,
    docker_command: str = "python -m app.main",
    docker_port: int | None = None,
    start_files: tuple[str, ...] = (),
    extra_ignore: str = "",
) -> ProjectSpec:
    files.extend(guidance_files(config))
    files.extend(
        standard_files(
            config,
            docker_command=docker_command,
            docker_port=docker_port,
            extra_ignore=extra_ignore,
        )
    )
    files.append(ProjectFile("pyproject.toml", project_toml(config, deps)))
    return ProjectSpec(tuple(files), deps, commands, start_files)


def _provider_file(config: ProjectConfig) -> ProjectFile:
    implementations = {
        Provider.OPENAI: """import os

from dotenv import load_dotenv

load_dotenv()

PROVIDER_CONFIGURED = True

def create_chat_model():
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError("Set OPENAI_API_KEY in .env before using the OpenAI model.")
    from langchain_openai import ChatOpenAI
    return ChatOpenAI(model="gpt-4o-mini")
""",
        Provider.GROQ: """import os

from dotenv import load_dotenv

load_dotenv()

PROVIDER_CONFIGURED = True

def create_chat_model():
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError("Set GROQ_API_KEY in .env before using the Groq model.")
    from langchain_groq import ChatGroq
    return ChatGroq(model="llama-3.1-8b-instant")
""",
        Provider.OLLAMA: """import os

from dotenv import load_dotenv
from langchain_ollama import ChatOllama

load_dotenv()

PROVIDER_CONFIGURED = True

def create_chat_model():
    return ChatOllama(model="llama3.2", base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"))
""",
        Provider.NONE: """PROVIDER_CONFIGURED = False

def create_chat_model():
    raise RuntimeError("No model provider is configured. Choose one or implement create_chat_model().")
""",
    }
    return ProjectFile("app/config/provider.py", implementations[config.provider])


def _vector_store_file(config: ProjectConfig) -> ProjectFile:
    implementations = {
        VectorStore.CHROMA: """import hashlib
import re
from pathlib import Path
from uuid import uuid4

import chromadb

DIMENSIONS = 256


def _embed(text: str) -> list[float]:
    vector = [0.0] * DIMENSIONS
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        index = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=2).digest(), "big") % DIMENSIONS
        vector[index] += 1.0
    magnitude = sum(value * value for value in vector) ** 0.5
    return [value / magnitude for value in vector] if magnitude else vector


class VectorStore:
    def __init__(self, path: str = "data/chroma") -> None:
        Path(path).mkdir(parents=True, exist_ok=True)
        client = chromadb.PersistentClient(path=path)
        self.collection = client.get_or_create_collection("documents")

    def add_documents(self, documents: list[str], source: str) -> None:
        if documents:
            self.collection.add(
                ids=[str(uuid4()) for _ in documents],
                documents=documents,
                embeddings=[_embed(document) for document in documents],
                metadatas=[{"source": source} for _ in documents],
            )

    def search(self, query: str, limit: int = 3) -> list[str]:
        count = self.collection.count()
        if count == 0:
            return []
        result = self.collection.query(query_embeddings=[_embed(query)], n_results=min(limit, count))
        return list((result.get("documents") or [[]])[0])


def create_vector_store():
    return VectorStore()
""",
        VectorStore.FAISS: """import hashlib
import re

import faiss
import numpy as np

DIMENSIONS = 256


def _embed(text: str) -> np.ndarray:
    vector = np.zeros(DIMENSIONS, dtype="float32")
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        index = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=2).digest(), "big") % DIMENSIONS
        vector[index] += 1
    norm = np.linalg.norm(vector)
    return vector / norm if norm else vector


class VectorStore:
    def __init__(self) -> None:
        self.index = faiss.IndexFlatIP(DIMENSIONS)
        self.documents: list[str] = []

    def add_documents(self, documents: list[str], source: str) -> None:
        del source
        if documents:
            self.index.add(np.stack([_embed(document) for document in documents]))
            self.documents.extend(documents)

    def search(self, query: str, limit: int = 3) -> list[str]:
        if not self.documents:
            return []
        _, indices = self.index.search(np.stack([_embed(query)]), min(limit, len(self.documents)))
        return [self.documents[index] for index in indices[0] if index >= 0]


def create_vector_store():
    return VectorStore()
""",
        VectorStore.PGVECTOR: """import hashlib
import os
import re

import psycopg
from dotenv import load_dotenv
from pgvector import Vector
from pgvector.psycopg import register_vector

load_dotenv()

DIMENSIONS = 256


def _embed(text: str) -> list[float]:
    vector = [0.0] * DIMENSIONS
    for token in re.findall(r"[a-z0-9]+", text.lower()):
        index = int.from_bytes(hashlib.blake2b(token.encode(), digest_size=2).digest(), "big") % DIMENSIONS
        vector[index] += 1.0
    magnitude = sum(value * value for value in vector) ** 0.5
    return [value / magnitude for value in vector] if magnitude else vector


class VectorStore:
    def __init__(self) -> None:
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise RuntimeError("Set DATABASE_URL in .env before using pgvector.")
        self.connection = psycopg.connect(database_url, autocommit=True)
        self.connection.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(self.connection)
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS documents "
            "(id bigserial PRIMARY KEY, source text NOT NULL, content text NOT NULL, embedding vector(256) NOT NULL)"
        )

    def add_documents(self, documents: list[str], source: str) -> None:
        with self.connection.cursor() as cursor:
            cursor.executemany(
                "INSERT INTO documents (source, content, embedding) VALUES (%s, %s, %s::vector)",
                [(source, document, Vector(_embed(document))) for document in documents],
            )

    def search(self, query: str, limit: int = 3) -> list[str]:
        rows = self.connection.execute(
            "SELECT content FROM documents ORDER BY embedding <=> %s::vector LIMIT %s",
            (Vector(_embed(query)), limit),
        ).fetchall()
        return [row[0] for row in rows]

def create_vector_store():
    return VectorStore()
""",
        VectorStore.NONE: """class VectorStore:
    def __init__(self) -> None:
        self.documents: list[str] = []

    def add_documents(self, documents: list[str], source: str) -> None:
        del source
        self.documents.extend(documents)

    def search(self, query: str, limit: int = 3) -> list[str]:
        terms = set(query.lower().split())
        ranked = sorted(
            self.documents,
            key=lambda document: len(terms & set(document.lower().split())),
            reverse=True,
        )
        return ranked[:limit]

def create_vector_store():
    return VectorStore()
""",
    }
    return ProjectFile("app/config/vector_store.py", implementations[config.vector_store])


def _provider_environment(config: ProjectConfig) -> str:
    if config.provider is Provider.NONE:
        return "No model provider is configured, so no `.env` file is required."
    return "Copy `.env.example` to `.env` and fill only the value for the selected provider."


def build_fastapi(config: ProjectConfig) -> ProjectSpec:
    deps = dependencies(("fastapi", "pydantic", "pydantic-settings", "python-dotenv", "uvicorn[standard]"))
    files = init_files("app", "app/api", "app/api/routes", "app/core", "app/schemas", "app/services")
    files += [
        ProjectFile(
            "app/main.py",
            """from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.api.routes.items import router as items_router
from app.core.config import settings

app = FastAPI(title=settings.app_name)
app.include_router(health_router)
app.include_router(items_router)
""",
        ),
        ProjectFile(
            "app/api/routes/health.py",
            """from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
""",
        ),
        ProjectFile(
            "app/core/config.py",
            """from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Generated API"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
""",
        ),
        ProjectFile(
            "app/schemas/items.py",
            '''from uuid import UUID

from pydantic import BaseModel, Field


class ItemCreate(BaseModel):
    """Validated input accepted by the API."""

    title: str = Field(min_length=1, max_length=200)
    completed: bool = False


class Item(ItemCreate):
    """Item returned by the API."""

    id: UUID
''',
        ),
        ProjectFile(
            "app/services/items.py",
            """from uuid import UUID, uuid4

from app.schemas.items import Item, ItemCreate

_items: dict[UUID, Item] = {}


def list_items() -> list[Item]:
    return list(_items.values())


def create_item(payload: ItemCreate) -> Item:
    item = Item(id=uuid4(), **payload.model_dump())
    _items[item.id] = item
    return item


def get_item(item_id: UUID) -> Item | None:
    return _items.get(item_id)
""",
        ),
        ProjectFile(
            "app/api/routes/items.py",
            """from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from app.schemas.items import Item, ItemCreate
from app.services import items

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[Item])
def list_items() -> list[Item]:
    return items.list_items()


@router.post("", response_model=Item, status_code=status.HTTP_201_CREATED)
def create_item(payload: ItemCreate) -> Item:
    return items.create_item(payload)


@router.get("/{item_id}", response_model=Item)
def get_item(item_id: UUID) -> Item:
    item = items.get_item(item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item
""",
        ),
        env_file(config, extra=("APP_NAME=Generated API",)),
    ]
    files += _tests(
        config,
        "tests/test_health.py",
        """from fastapi.testclient import TestClient

from app.main import app


def test_health() -> None:
    response = TestClient(app).get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_and_get_item() -> None:
    client = TestClient(app)
    assert client.post("/items", json={"title": ""}).status_code == 422

    created = client.post("/items", json={"title": "Write business logic"})
    assert created.status_code == 201
    item = created.json()
    assert item["title"] == "Write business logic"

    fetched = client.get(f"/items/{item['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == item


def test_missing_item_returns_404() -> None:
    response = TestClient(app).get("/items/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json() == {"detail": "Item not found"}
""",
    )
    files.append(
        ProjectFile(
            "README.md",
            readme(
                config,
                template_name="FastAPI Backend",
                summary="A small production-ready HTTP API with a health endpoint.",
                tree="app/ (API, configuration, schemas, services)\ntests/\npyproject.toml",
                run="uvicorn app.main:app --reload",
                architecture="Routes handle HTTP concerns, services hold business logic, and configuration is loaded independently.",
                important="`app/main.py` creates the application; `schemas/items.py` validates API data; `services/items.py` is the business-logic seam; `api/routes/items.py` maps HTTP requests to that service.",
                start_here=(
                    "Copy `.env.example` to `.env`.",
                    "Open `app/services/items.py` and replace the in-memory example with your business rules.",
                    "Adapt `app/schemas/items.py` to your domain data.",
                    "Add or rename endpoints in `app/api/routes/items.py`.",
                    "Run `uvicorn app.main:app --reload` and open `/docs`.",
                ),
                environment="Copy `.env.example` to `.env` and customize `APP_NAME` if desired.",
                docker_port=8000,
            ),
        )
    )
    return _spec(
        config,
        files,
        deps,
        ("uvicorn app.main:app --reload",),
        docker_command="uvicorn app.main:app --host 0.0.0.0 --port 8000",
        docker_port=8000,
        start_files=("app/services/items.py", "app/schemas/items.py", "app/api/routes/items.py"),
    )


def build_rag(config: ProjectConfig) -> ProjectSpec:
    deps = dependencies(
        ("pypdf",),
        ("python-dotenv",)
        if config.provider is not Provider.NONE or config.vector_store is VectorStore.PGVECTOR
        else (),
        provider_dependencies(config),
        vector_dependencies(config),
        ("fastapi", "pydantic", "uvicorn[standard]") if config.include_api else (),
    )
    files = init_files("app", "app/rag", "app/loaders", "app/config")
    files += [
        ProjectFile(
            "app/loaders/documents.py",
            '''from pathlib import Path

def load_document(path: str | Path) -> str:
    """Load a UTF-8 text file or extract text from a PDF."""
    document_path = Path(path)
    if document_path.suffix.lower() == ".pdf":
        from pypdf import PdfReader

        return "\\n".join(page.extract_text() or "" for page in PdfReader(document_path).pages)
    return document_path.read_text(encoding="utf-8")
''',
        ),
        ProjectFile(
            "app/rag/ingestion.py",
            '''def chunk_document(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    """Split a document into overlapping, non-empty character chunks."""
    if size <= 0 or overlap < 0 or overlap >= size:
        raise ValueError("Require size > 0 and 0 <= overlap < size")
    cleaned = text.strip()
    if not cleaned:
        return []
    step = size - overlap
    return [cleaned[index:index + size] for index in range(0, len(cleaned), step)]
''',
        ),
        ProjectFile(
            "app/rag/retrieval.py",
            '''from typing import Protocol


class SearchableStore(Protocol):
    def search(self, query: str, limit: int = 3) -> list[str]: ...


def retrieve(store: SearchableStore, query: str, limit: int = 3) -> list[str]:
    """Retrieve the most relevant chunks through the configured store."""
    return store.search(query, limit)
''',
        ),
        ProjectFile(
            "app/rag/prompts.py",
            '''RAG_PROMPT = """Answer the question using only the supplied context.
If the answer is absent, say that you do not know.

Context:
{context}

Question: {question}
"""
''',
        ),
        ProjectFile(
            "app/rag/pipeline.py",
            """from pathlib import Path

from app.config.provider import PROVIDER_CONFIGURED, create_chat_model
from app.config.vector_store import create_vector_store
from app.loaders.documents import load_document
from app.rag.ingestion import chunk_document
from app.rag.prompts import RAG_PROMPT
from app.rag.retrieval import retrieve


class RAGPipeline:
    def __init__(self, store=None) -> None:
        self.store = store or create_vector_store()

    def ingest_text(self, text: str, source: str = "document") -> int:
        chunks = chunk_document(text)
        self.store.add_documents(chunks, source)
        return len(chunks)

    def ingest_path(self, path: str | Path) -> int:
        return self.ingest_text(load_document(path), str(path))

    def answer(self, question: str) -> str:
        context = retrieve(self.store, question)
        if not context:
            return "No relevant context found."
        joined_context = "\\n\\n".join(context)
        if not PROVIDER_CONFIGURED:
            return "Retrieved context:\\n" + joined_context
        prompt = RAG_PROMPT.format(context=joined_context, question=question)
        response = create_chat_model().invoke(prompt)
        return str(response.content)
""",
        ),
        ProjectFile(
            "app/main.py",
            """from app.rag.pipeline import RAGPipeline


def main() -> None:
    pipeline = RAGPipeline()
    pipeline.ingest_text("Retrieval finds relevant document chunks before generation.", "example")
    print(pipeline.answer("What is retrieval?"))


if __name__ == "__main__":
    main()
""",
        ),
        _provider_file(config),
        _vector_store_file(config),
        ProjectFile("data/.gitkeep", ""),
    ]
    if config.provider is not Provider.NONE or config.vector_store is VectorStore.PGVECTOR:
        files.append(env_file(config))
    if config.include_api:
        files.append(
            ProjectFile(
                "app/api.py",
                """from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.rag.pipeline import RAGPipeline

app = FastAPI(title="RAG API")
pipeline = RAGPipeline()

class DocumentInput(BaseModel):
    text: str
    source: str = "api"

class QueryInput(BaseModel):
    question: str

@app.post("/documents", status_code=201)
def ingest(payload: DocumentInput) -> dict[str, int]:
    return {"chunks": pipeline.ingest_text(payload.text, payload.source)}

@app.post("/query")
def query(payload: QueryInput) -> dict[str, str]:
    answer = pipeline.answer(payload.question)
    if answer == "No relevant context found.":
        raise HTTPException(status_code=404, detail=answer)
    return {"answer": answer}
""",
            )
        )
    files += _tests(
        config,
        "tests/test_pipeline.py",
        """from app.rag.pipeline import RAGPipeline


class FakeStore:
    def __init__(self) -> None:
        self.documents: list[str] = []

    def add_documents(self, documents: list[str], source: str) -> None:
        del source
        self.documents.extend(documents)

    def search(self, query: str, limit: int = 3) -> list[str]:
        del query
        return self.documents[:limit]


def test_pipeline_returns_context() -> None:
    pipeline = RAGPipeline(store=FakeStore())
    assert pipeline.ingest_text("retrieval grounds an answer") == 1
    assert pipeline.store.documents == ["retrieval grounds an answer"]
""",
    )
    run = "uvicorn app.api:app --reload" if config.include_api else "python -m app.main"
    env_note = _provider_environment(config)
    if config.vector_store is VectorStore.PGVECTOR:
        env_note += " Set `DATABASE_URL` for pgvector."
    embedding_note = (
        " The generated vector adapter uses deterministic hashing embeddings for local wiring and tests, not production semantic retrieval. Replace `_embed` in `app/config/vector_store.py` with an embedding model suited to your documents."
        if config.vector_store is not VectorStore.NONE
        else ""
    )
    files.append(
        ProjectFile(
            "README.md",
            readme(
                config,
                template_name="RAG Application",
                summary=f"A focused retrieval-augmented generation starter (provider: {config.provider.value}, vector store: {config.vector_store.value}).",
                tree="app/loaders/\napp/rag/ (ingestion -> retrieval -> pipeline)\napp/config/\ndata/\ntests/",
                run=run,
                architecture="Documents are loaded, chunked, stored through the selected vector integration, retrieved, and passed to the selected model. With no provider, the same pipeline returns its retrieved context locally."
                + embedding_note,
                important="`loaders/documents.py` reads text and PDFs; `ingestion.py` chunks them; `retrieval.py` uses the selected store; `prompts.py` owns model instructions; `pipeline.py` coordinates the complete flow.",
                start_here=(
                    "Copy `.env.example` to `.env` when it exists and fill the selected integration values.",
                    "Put a text or PDF document in `data/`, then call `RAGPipeline.ingest_path(...)` from `app/main.py`.",
                    "Adapt chunking in `app/rag/ingestion.py` and the instructions in `app/rag/prompts.py`.",
                    f"Run `{run}`; with the API option, POST documents to `/documents` before querying `/query`.",
                ),
                environment=env_note,
                docker_port=8000 if config.include_api else None,
            ),
        )
    )
    docker_command = "uvicorn app.api:app --host 0.0.0.0 --port 8000" if config.include_api else run
    return _spec(
        config,
        files,
        deps,
        (run,),
        docker_command=docker_command,
        docker_port=8000 if config.include_api else None,
        start_files=("app/loaders/documents.py", "app/rag/prompts.py", "app/rag/pipeline.py"),
        extra_ignore="data/*\n!data/.gitkeep\n",
    )


def build_agent(config: ProjectConfig) -> ProjectSpec:
    deps = dependencies(("langchain-core",), provider_dependencies(config))
    files = init_files("app", "app/agent", "app/config")
    files += [
        ProjectFile(
            "app/agent/tools.py",
            '''from langchain_core.tools import tool


@tool
def word_count(text: str) -> str:
    """Count the words in the supplied text."""
    return str(len(text.split()))

TOOLS = [word_count]
TOOL_MAP = {item.name: item for item in TOOLS}
''',
        ),
        ProjectFile(
            "app/agent/prompts.py", 'SYSTEM_PROMPT = "You are a concise assistant. Use a tool when it helps."\n'
        ),
        ProjectFile(
            "app/agent/agent.py",
            '''from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from app.agent.prompts import SYSTEM_PROMPT
from app.agent.tools import TOOLS, TOOL_MAP
from app.config.provider import create_chat_model


def run_agent(message: str, max_tool_rounds: int = 4) -> str:
    """Let the selected model choose and execute tools using native tool calls."""
    model = create_chat_model().bind_tools(TOOLS)
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=message)]
    response = model.invoke(messages)
    for _ in range(max_tool_rounds):
        if not response.tool_calls:
            return str(response.content)
        messages.append(response)
        for call in response.tool_calls:
            tool = TOOL_MAP.get(call["name"])
            if tool is None:
                result = f"Unknown tool: {call['name']}"
            else:
                result = tool.invoke(call["args"])
            messages.append(ToolMessage(content=str(result), tool_call_id=call["id"]))
        response = model.invoke(messages)
    return str(response.content)
''',
        ),
        ProjectFile(
            "app/main.py",
            """from app.agent.agent import run_agent
from app.agent.tools import word_count
from app.config.provider import PROVIDER_CONFIGURED

if __name__ == "__main__":
    if not PROVIDER_CONFIGURED:
        print("Local tool result:", word_count.invoke({"text": "build small reliable agents"}))
        print("Choose a model provider or implement app/config/provider.py to enable model-selected tools.")
    else:
        print(run_agent("How many words are in: build small reliable agents?"))
""",
        ),
        _provider_file(config),
    ]
    if config.provider is not Provider.NONE:
        files.append(env_file(config))
    files += _tests(
        config,
        "tests/test_agent.py",
        """from app.agent.tools import word_count

def test_word_count_tool() -> None:
    assert word_count.invoke({"text": "one two three"}) == "3"
""",
    )
    files.append(
        ProjectFile(
            "README.md",
            readme(
                config,
                template_name="AI Agent",
                summary=f"A transparent tool-using agent starter configured for {config.provider.value}.",
                tree="app/agent/ (agent, prompts, tools)\napp/config/\ntests/",
                run="python -m app.main",
                architecture="Prompts define behavior, tools use LangChain's native schema, and the selected chat model chooses tool calls. The explicit loop executes each call and returns its result to the model.",
                important="`agent.py` orchestrates, `tools.py` exposes capabilities, `prompts.py` contains instructions, and `config/provider.py` creates the selected model.",
                start_here=(
                    "Copy `.env.example` to `.env` when it exists and add the selected provider key.",
                    "Open `app/agent/tools.py` and replace or extend the example tool with your domain operations.",
                    "Edit `app/agent/prompts.py` to define the agent's role and boundaries.",
                    "Run `python -m app.main` and ask a question that requires your tool.",
                ),
                environment=_provider_environment(config),
            ),
        )
    )
    return _spec(
        config,
        files,
        deps,
        ("python -m app.main",),
        start_files=("app/agent/tools.py", "app/agent/prompts.py", "app/agent/agent.py"),
    )


def build_langgraph(config: ProjectConfig) -> ProjectSpec:
    deps = dependencies(("langchain-core", "langgraph"), provider_dependencies(config))
    node_source = (
        """from app.graph.state import GraphState
from app.tools.text import normalize_text


def process(state: GraphState) -> GraphState:
    return {**state, "result": normalize_text(state["message"])}
"""
        if config.provider is Provider.NONE
        else """from app.config.provider import create_chat_model
from app.graph.state import GraphState


def process(state: GraphState) -> GraphState:
    response = create_chat_model().invoke(state["message"])
    return {**state, "result": str(response.content)}
"""
    )
    files = init_files("app", "app/graph", "app/tools", "app/config")
    files += [
        ProjectFile(
            "app/graph/state.py",
            """from typing import TypedDict

class GraphState(TypedDict):
    message: str
    result: str
""",
        ),
        ProjectFile(
            "app/graph/nodes.py",
            node_source,
        ),
        ProjectFile(
            "app/tools/text.py",
            '''def normalize_text(value: str) -> str:
    """A local node dependency that remains useful without a model provider."""
    return " ".join(value.split()).upper()
''',
        ),
        ProjectFile(
            "app/graph/graph.py",
            """from langgraph.graph import END, START, StateGraph
from app.graph.nodes import process
from app.graph.state import GraphState

builder = StateGraph(GraphState)
builder.add_node("process", process)
builder.add_edge(START, "process")
builder.add_edge("process", END)
graph = builder.compile()
""",
        ),
        ProjectFile(
            "app/main.py",
            """from app.graph.graph import graph

if __name__ == "__main__":
    print(graph.invoke({"message": "hello graph", "result": ""})["result"])
""",
        ),
        _provider_file(config),
    ]
    if config.provider is not Provider.NONE:
        files.append(env_file(config))
    graph_test = (
        """from app.graph.graph import graph

def test_graph_transitions() -> None:
    assert graph.invoke({"message": "hello   graph", "result": ""})["result"] == "HELLO GRAPH"
"""
        if config.provider is Provider.NONE
        else """from app.graph.graph import graph

def test_graph_is_compiled() -> None:
    assert "process" in graph.get_graph().nodes
"""
    )
    files += _tests(
        config,
        "tests/test_graph.py",
        graph_test,
    )
    files.append(
        ProjectFile(
            "README.md",
            readme(
                config,
                template_name="LangGraph Agent",
                summary=f"A minimal executable LangGraph starter configured for {config.provider.value}.",
                tree="app/graph/ (state, nodes, graph)\napp/tools/\napp/config/\ntests/",
                run="python -m app.main",
                architecture="`GraphState` flows from START through the `process` node to END. Add nodes and explicit edges as the workflow grows.",
                important="`state.py` defines shared state, `nodes.py` performs the configured transformation, `graph.py` wires edges, and `tools/text.py` demonstrates a reusable local operation.",
                start_here=(
                    "Copy `.env.example` to `.env` when it exists and configure the selected model.",
                    "Define the data your workflow carries in `app/graph/state.py`.",
                    "Replace the example transformation in `app/graph/nodes.py`, extracting reusable operations into `app/tools/`.",
                    "Wire the next node and edge explicitly in `app/graph/graph.py`, then run `python -m app.main`.",
                ),
                environment=_provider_environment(config),
            ),
        )
    )
    return _spec(
        config,
        files,
        deps,
        ("python -m app.main",),
        start_files=("app/graph/state.py", "app/graph/nodes.py", "app/graph/graph.py"),
    )


def build_ml(config: ProjectConfig) -> ProjectSpec:
    package = config.package_name
    deps = dependencies(("joblib", "numpy", "pandas", "scikit-learn"))
    files = init_files(f"src/{package}", f"src/{package}/data", f"src/{package}/features", f"src/{package}/models")
    files += [
        ProjectFile(
            f"src/{package}/data/load.py",
            '''from pathlib import Path

import pandas as pd
from sklearn.datasets import load_iris


def load_dataset(path: str | Path | None = None) -> tuple[pd.DataFrame, pd.Series]:
    """Load a CSV with a target column, or the runnable Iris example."""
    if path is None:
        dataset = load_iris(as_frame=True)
        return dataset.data, dataset.target
    frame = pd.read_csv(path)
    if "target" not in frame:
        raise ValueError("Input CSV must contain a 'target' column")
    return frame.drop(columns="target"), frame["target"]
''',
        ),
        ProjectFile(
            f"src/{package}/features/build.py",
            '''from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler


def build_preprocessor() -> Pipeline:
    """Create the feature steps fitted only on training data."""
    return Pipeline([("impute", SimpleImputer()), ("scale", StandardScaler())])
''',
        ),
        ProjectFile(
            f"src/{package}/models/train.py",
            f"""from pathlib import Path

import joblib
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from {package}.data.load import load_dataset
from {package}.features.build import build_preprocessor


def train(data_path: str | Path | None = None, model_path: str | Path = "models/model.joblib") -> float:
    features, target = load_dataset(data_path)
    train_x, test_x, train_y, test_y = train_test_split(
        features, target, test_size=0.2, random_state=42, stratify=target
    )
    model = Pipeline([("features", build_preprocessor()), ("model", LogisticRegression(max_iter=300))])
    model.fit(train_x, train_y)
    destination = Path(model_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, destination)
    return float(model.score(test_x, test_y))


if __name__ == "__main__":
    print("validation accuracy:", train())
""",
        ),
        ProjectFile("data/raw/.gitkeep", ""),
        ProjectFile("data/processed/.gitkeep", ""),
        ProjectFile("notebooks/.gitkeep", ""),
        ProjectFile("models/.gitkeep", ""),
    ]
    files += _tests(
        config,
        "tests/test_train.py",
        f"""from {package}.models.train import train

def test_training_persists_model(tmp_path) -> None:
    model_path = tmp_path / "model.joblib"
    score = train(model_path=model_path)
    assert 0.0 <= score <= 1.0
    assert model_path.is_file()
""",
    )
    run = f"python -m {package}.models.train"
    files.extend(guidance_files(config))
    files.extend(
        standard_files(
            config,
            extra_ignore="data/raw/*\ndata/processed/*\n!data/raw/.gitkeep\n!data/processed/.gitkeep\nmodels/*\n!models/.gitkeep\n.ipynb_checkpoints/\n",
            docker_command=run,
        )
    )
    files += [
        ProjectFile("pyproject.toml", project_toml(config, deps, package_path=f"src/{package}")),
        ProjectFile(
            "README.md",
            readme(
                config,
                template_name="Machine Learning",
                summary="A reproducible classical machine-learning project with separated data, feature, and model code.",
                tree=f"data/{{raw,processed}}/\nnotebooks/\nsrc/{package}/{{data,features,models}}/\nmodels/\ntests/",
                run=run,
                architecture="Raw data is immutable input; transformations create processed data and features; training code produces versionable model artifacts.",
                important="`data/load.py` owns input contracts, `features/build.py` fits preprocessing inside the model pipeline, and `models/train.py` evaluates and persists `models/model.joblib`.",
                start_here=(
                    f"Put your CSV in `data/raw/` with a `target` column, then pass its path in `src/{package}/models/train.py`.",
                    f"Implement domain transformations in `src/{package}/features/build.py`.",
                    f"Choose and tune the estimator in `src/{package}/models/train.py`.",
                    f"Run `{run}` and inspect the saved `models/model.joblib` artifact.",
                ),
            ),
        ),
    ]
    return ProjectSpec(
        tuple(files),
        deps,
        (run,),
        (f"src/{package}/data/load.py", f"src/{package}/features/build.py", f"src/{package}/models/train.py"),
    )


def build_data_science(config: ProjectConfig) -> ProjectSpec:
    package = config.package_name
    deps = dependencies(("jupyterlab", "matplotlib", "numpy", "pandas", "seaborn"))
    files = init_files(f"src/{package}")
    files += [
        ProjectFile(
            f"src/{package}/io.py",
            '''from pathlib import Path

import pandas as pd


def load_raw_csv(path: str | Path) -> pd.DataFrame:
    """Load a raw dataset without mutating the source file."""
    return pd.read_csv(path)
''',
        ),
        ProjectFile(
            f"src/{package}/analysis.py",
            """import pandas as pd

def summarize(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.describe(include="all")
""",
        ),
        ProjectFile("data/raw/.gitkeep", ""),
        ProjectFile("data/processed/.gitkeep", ""),
        ProjectFile("notebooks/.gitkeep", ""),
        ProjectFile("reports/figures/.gitkeep", ""),
    ]
    files += _tests(
        config,
        "tests/test_analysis.py",
        f"""import pandas as pd
from {package}.analysis import summarize

def test_summarize() -> None:
    assert "value" in summarize(pd.DataFrame({{"value": [1, 2]}})).columns
""",
    )
    files.extend(guidance_files(config))
    files.extend(
        standard_files(
            config,
            extra_ignore="data/raw/*\ndata/processed/*\n!data/raw/.gitkeep\n!data/processed/.gitkeep\nreports/figures/*\n!reports/figures/.gitkeep\n.ipynb_checkpoints/\n",
            docker_command="jupyter lab --no-browser --ip=0.0.0.0 --allow-root",
            docker_port=8888,
        )
    )
    files += [
        ProjectFile("pyproject.toml", project_toml(config, deps, package_path=f"src/{package}")),
        ProjectFile(
            "README.md",
            readme(
                config,
                template_name="Data Science",
                summary="A tidy analysis workspace for notebooks, reusable code, data, and reports.",
                tree=f"data/{{raw,processed}}/\nnotebooks/\nsrc/{package}/\nreports/figures/\ntests/",
                run="jupyter lab",
                architecture="Notebooks explore; the import package contains reusable transformations; durable figures and reports stay separate from raw data.",
                important=f"`src/{package}/io.py` owns data loading, `analysis.py` holds reusable analysis, and `notebooks/` is reserved for exploration and communication.",
                start_here=(
                    "Put an immutable source CSV in `data/raw/`.",
                    f"Load it through `src/{package}/io.py` and add reusable transformations to `analysis.py`.",
                    "Create an exploration notebook that imports the package instead of duplicating durable logic.",
                    "Save cleaned outputs in `data/processed/` and durable charts in `reports/figures/`.",
                ),
                docker_port=8888,
            ),
        ),
    ]
    return ProjectSpec(
        tuple(files),
        deps,
        ("jupyter lab",),
        (f"src/{package}/io.py", f"src/{package}/analysis.py", "notebooks/"),
    )


def build_cli(config: ProjectConfig) -> ProjectSpec:
    package = config.package_name
    deps = dependencies(("typer>=0.12",))
    files = init_files(f"src/{package}")
    files += [
        ProjectFile(
            f"src/{package}/cli.py",
            f'''from importlib.metadata import PackageNotFoundError, version

import typer

try:
    VERSION = version("{config.project_name}")
except PackageNotFoundError:
    VERSION = "0.1.0"

app = typer.Typer(help="A generated command-line application.")

def version_callback(value: bool) -> None:
    if value:
        typer.echo(VERSION)
        raise typer.Exit()

@app.callback()
def main(version_flag: bool = typer.Option(False, "--version", callback=version_callback, is_eager=True)) -> None:
    """Run the generated command-line application."""

@app.command()
def hello(name: str) -> None:
    """Greet someone."""
    typer.echo(f"Hello, {{name}}!")

if __name__ == "__main__":
    app()
''',
        )
    ]
    files += _tests(
        config,
        "tests/test_cli.py",
        f"""from typer.testing import CliRunner
from {package}.cli import app

def test_hello() -> None:
    hello = CliRunner().invoke(app, ["hello", "Ada"])
    assert hello.exit_code == 0
    assert "Hello, Ada!" in hello.stdout

    version = CliRunner().invoke(app, ["--version"])
    assert version.exit_code == 0
    assert "0.1.0" in version.stdout
""",
    )
    files.extend(guidance_files(config))
    files.extend(standard_files(config, docker_command=f"{config.project_name} hello world"))
    files += [
        ProjectFile(
            "pyproject.toml",
            project_toml(
                config, deps, script=(config.project_name, f"{package}.cli:app"), package_path=f"src/{package}"
            ),
        ),
        ProjectFile(
            "README.md",
            readme(
                config,
                template_name="Python CLI",
                summary="An installable Typer command-line application with a console entry point.",
                tree=f"src/{package}/\ntests/\npyproject.toml",
                run=f"{config.project_name} --help\n{config.project_name} --version\n{config.project_name} hello Ada",
                architecture="Typer maps typed Python functions to commands. The console script imports the single application object.",
                important=f"`src/{package}/cli.py` owns commands; `[project.scripts]` in `pyproject.toml` exposes `{config.project_name}`.",
                start_here=(
                    f"Open `src/{package}/cli.py` and rename the example `hello` command for your first workflow.",
                    "Add typed parameters and options to that function; Typer turns them into CLI help and validation.",
                    "Move substantial business logic into a sibling module and keep the command focused on input and output.",
                    f"Run `{config.project_name} --help`, then exercise the command and update `tests/test_cli.py`.",
                ),
            ),
        ),
    ]
    return ProjectSpec(
        tuple(files),
        deps,
        (f"{config.project_name} hello Ada",),
        (f"src/{package}/cli.py", "tests/test_cli.py"),
    )
