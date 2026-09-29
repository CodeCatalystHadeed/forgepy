# Contributing to ForgePy

Thanks for helping improve ForgePy. Use Python 3.11 or newer, create a virtual environment, and install the development dependencies:

```console
python -m venv .venv
# Windows PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m ruff check .
python -m pytest
python -m build
```

Keep changes focused and add tests for behavior. Run the full suite before opening a pull request. Generated projects must compile and must never overwrite pre-existing files.

## Adding a template

1. Add one builder returning `ProjectSpec` in `src/forgepy/templates/builders.py` (or a focused new module).
2. Describe it with a `Template` in `src/forgepy/registry/templates.py`.
3. Add a generation case that parses its `pyproject.toml` and compiles every Python file.
4. Document its command and purpose in `README.md`.

The CLI and generation engine must not branch on template IDs. Optional behavior belongs in metadata and the builder.

## Pull requests

Keep generated files deterministic, avoid real secrets in fixtures, and document user-visible behavior. Security reports belong in the private channel described by `SECURITY.md`, not in public issues.
