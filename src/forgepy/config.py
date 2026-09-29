"""Validated input passed from the CLI to template builders."""

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class PackageManager(StrEnum):
    PIP = "pip"
    UV = "uv"


class Provider(StrEnum):
    OPENAI = "openai"
    GROQ = "groq"
    OLLAMA = "ollama"
    NONE = "none"


class VectorStore(StrEnum):
    CHROMA = "chroma"
    FAISS = "faiss"
    PGVECTOR = "pgvector"
    NONE = "none"


class Guidance(StrEnum):
    LEARNING = "learning"
    STANDARD = "standard"
    MINIMAL = "minimal"


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    project_name: str
    package_name: str
    destination: Path
    template_id: str
    python_version: str = "3.12"
    package_manager: PackageManager = PackageManager.PIP
    include_tests: bool = True
    include_docker: bool = False
    provider: Provider = Provider.NONE
    vector_store: VectorStore = VectorStore.NONE
    include_api: bool = False
    guidance: Guidance = Guidance.STANDARD
    setup: bool = False
