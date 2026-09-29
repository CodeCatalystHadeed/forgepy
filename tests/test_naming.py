import pytest

from forgepy.utils.naming import (
    MAX_PROJECT_NAME_LENGTH,
    InvalidProjectName,
    distribution_name,
    import_name,
    validate_project_name,
)


@pytest.mark.parametrize("name", ["my-api", "My API", "data_tool", "project.v2"])
def test_valid_names(name: str) -> None:
    assert validate_project_name(name) == name


@pytest.mark.parametrize(
    "name",
    [
        "",
        " ",
        ".",
        "..",
        "../escape",
        "../../test",
        "/tmp/test",
        "a/b",
        "a\\b",
        "C:\\escape",
        "CON",
        "PRN",
        "AUX",
        "NUL",
        "COM1",
        "LPT1",
        "nul.txt",
        "bad?name",
        "project$name",
        "ü-project",
        " trailing",
        "trailing.",
        "___",
        "---",
    ],
)
def test_dangerous_names(name: str) -> None:
    with pytest.raises(InvalidProjectName):
        distribution_name(name)


def test_extremely_long_name_is_rejected() -> None:
    with pytest.raises(InvalidProjectName, match="exceed"):
        validate_project_name("a" * (MAX_PROJECT_NAME_LENGTH + 1))


def test_normalization_distinguishes_distribution_and_import() -> None:
    assert distribution_name("My Awesome.API") == "my-awesome-api"
    assert import_name("My Awesome.API") == "my_awesome_api"
    assert import_name("42 tools") == "project_42_tools"
    assert import_name("class") == "class_project"
