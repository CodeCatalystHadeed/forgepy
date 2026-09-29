import pytest

from forgepy.models import ProjectFile, ProjectSpec, Template, TemplateError, TemplateRegistry
from forgepy.registry import registry


def _builder(config):
    return ProjectSpec((ProjectFile("README.md", "ok"),), (), ())


def test_all_expected_templates_registered() -> None:
    assert set(registry.as_mapping()) == {"fastapi", "rag", "agent", "langgraph", "ml", "data-science", "cli"}
    assert all(item.display_name and item.description for item in registry.all())


def test_duplicate_ids_are_rejected() -> None:
    local = TemplateRegistry()
    local.register(Template("demo", "Demo", "description", _builder))
    with pytest.raises(TemplateError, match="Duplicate"):
        local.register(Template("demo", "Again", "description", _builder))


@pytest.mark.parametrize("template_id", ["Bad ID", "UPPER", "", "é", "two--hyphens"])
def test_malformed_template_metadata_is_rejected(template_id: str) -> None:
    with pytest.raises(TemplateError):
        Template(template_id, "Demo", "description", _builder)


def test_unsafe_and_duplicate_template_paths_are_rejected() -> None:
    with pytest.raises(TemplateError):
        ProjectFile("../outside", "bad")
    for path in ("..\\outside", "C:\\outside", "/outside", "CON", "folder/NUL.txt", "bad?/file"):
        with pytest.raises(TemplateError):
            ProjectFile(path, "bad")
    with pytest.raises(TemplateError, match="duplicate"):
        ProjectSpec((ProjectFile("same", "a"), ProjectFile("same", "b")), (), ())
