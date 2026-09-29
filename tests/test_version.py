from importlib.metadata import version

from forgepy import __version__


def test_runtime_version_matches_package_metadata() -> None:
    assert __version__ == version("forgepy") == "1.0.0"
