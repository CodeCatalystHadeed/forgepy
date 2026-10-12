import tomllib
from importlib.metadata import distribution
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_project_metadata_is_consistent() -> None:
    with (ROOT / "pyproject.toml").open("rb") as handle:
        project = tomllib.load(handle)["project"]

    assert project["name"] == "forgepy"
    assert project["version"] == "1.0.0"
    assert project["requires-python"] == ">=3.11"
    assert project["license"] == "MIT"
    assert project["license-files"] == ["LICENSE"]
    assert not any(classifier.startswith("License ::") for classifier in project["classifiers"])
    assert project["scripts"]["forgepy"] == "forgepy.cli:app"


def test_installed_console_entry_point() -> None:
    entry_points = {entry.name: entry.value for entry in distribution("forgepy").entry_points}
    assert entry_points["forgepy"] == "forgepy.cli:app"
