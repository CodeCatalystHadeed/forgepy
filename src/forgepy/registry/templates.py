"""Built-in template registration."""

from forgepy.models import Template, TemplateRegistry
from forgepy.templates.builders import (
    build_agent,
    build_cli,
    build_data_science,
    build_fastapi,
    build_langgraph,
    build_ml,
    build_rag,
)

registry = TemplateRegistry()

for template in (
    Template("fastapi", "FastAPI Backend", "A structured HTTP API", build_fastapi),
    Template("rag", "RAG Application", "Retrieval-augmented generation pipeline", build_rag, True, True, True),
    Template("agent", "AI Agent", "A small tool-using agent", build_agent, True),
    Template("langgraph", "LangGraph Agent", "An explicit state graph", build_langgraph, True),
    Template("ml", "Machine Learning", "A reproducible model training layout", build_ml),
    Template("data-science", "Data Science", "An analysis and notebook workspace", build_data_science),
    Template("cli", "Python CLI", "An installable Typer command", build_cli),
):
    registry.register(template)
