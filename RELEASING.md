# Releasing ForgePy

Only a repository owner should perform these steps. The release workflows do not publish during ordinary CI.

## One-time owner setup

1. Confirm the canonical repository is <https://github.com/CodeCatalystHadeed/forgepy> and that the URLs in `pyproject.toml` still match it.
2. Confirm the intended PyPI distribution name immediately before release. The absence of a PyPI project page does not reserve a name. If the distribution name changes, update `[project].name`, installation documentation, the PyPI environment configuration, and the Trusted Publisher; the Python import and `forgepy` console command may remain unchanged.
3. In GitHub, create an environment named `pypi`. Add a required reviewer and restrict deployment to protected release tags where your plan supports it.
4. Protect the default branch, require CI before merging, and protect tags matching `v*` from untrusted creation or modification.
5. Enable private vulnerability reporting in the repository's **Security** settings.
6. In PyPI, configure a pending Trusted Publisher with the exact GitHub owner `CodeCatalystHadeed`, repository `forgepy`, workflow filename `publish.yml`, and environment `pypi`. A pending publisher does not reserve the project name.

## Prepare version 1.0.0

1. Start from a clean checkout of the default branch.
2. Confirm `pyproject.toml` contains `version = "1.0.0"`, `forgepy --version` reports `1.0.0`, and `CHANGELOG.md` has the final `1.0.0` entry.
3. Run:

   ```console
   python -m pip install -e ".[dev]" twine
   python -m ruff check .
   python -m ruff format --check .
   python -m pytest --cov=forgepy --cov-report=term-missing
   python -m build
   python -m twine check dist/*
   ```

4. Inspect both archives and repeat the isolated wheel and sdist smoke tests described by CI.
5. Commit the final release preparation and wait for required CI checks to pass.

## Publish through GitHub and PyPI

1. Create an annotated local tag at the reviewed commit:

   ```console
   git tag -a v1.0.0 -m "ForgePy 1.0.0"
   git push origin v1.0.0
   ```

2. Create a GitHub Release for tag `v1.0.0`. Review the generated notes, attach no locally built artifacts, and publish the release intentionally.
3. The `Publish to PyPI` workflow rebuilds from the tagged source, verifies that `v1.0.0` matches package metadata, runs tests and metadata checks, and pauses at the protected `pypi` environment.
4. Review and approve the `pypi` environment deployment. The final job receives only `id-token: write`, downloads the workflow-built artifacts, and publishes through PyPI Trusted Publishing.
5. Verify the PyPI project page, hashes, wheel and sdist files, project description, and a clean installation from PyPI.

The manual workflow dispatch is an emergency owner path. Enter `1.0.0` exactly and select the reviewed release commit; the workflow still requires environment approval and refuses a version mismatch.
