# ForgePy release readiness

Audit date: 2026-10-12

## A. Release verdict

**READY WITH MANUAL PUBLISHING PREREQUISITES**

ForgePy's source, generated projects, wheel, and source distribution pass the available local quality and installation gates. The owner must still configure the protected `pypi` GitHub environment and matching PyPI Trusted Publisher, confirm that PyPI permits registration of the exact `forgepy` name, merge the reviewed changes, and run the deliberate release process. Nothing was published, tagged, pushed, or released during this audit.

## B. Issues found and fixed

### PEP 639 metadata conflict

- **Problem:** `pyproject.toml` combined the SPDX expression `license = "MIT"` with the deprecated `License :: OSI Approved :: MIT License` classifier, while allowing Hatchling versions older than its PEP 639 support.
- **Impact:** Metadata 2.4 deprecates license classifiers, and current build tools may reject the combination. Hatchling added PEP 639 support in 1.27.0.
- **Fix:** Removed the legacy license classifier, retained the SPDX expression and explicit license file, and raised the build requirement to `hatchling>=1.27` in ForgePy and generated projects.
- **Verification:** A clean build emitted `License-Expression: MIT` and `License-File: LICENSE`; Twine and the archive validator passed.

### Distribution contents were not programmatically audited

- **Problem:** CI built and installed artifacts but did not assert the complete module set, license placement, entry point, rebuild inputs, or absence of common sensitive/cache files.
- **Impact:** A successful build alone can omit runtime files or ship unwanted local artifacts.
- **Fix:** Added `scripts/validate_dist.py` and wired it into CI, TestPyPI, and production publishing builds.
- **Verification:** The validator passed against the final wheel and sdist and confirmed all ForgePy modules, PEP 639 license placement, and `forgepy = forgepy.cli:app`.

### Installed-package smoke coverage was narrow

- **Problem:** CI generated only one template from the wheel and one from the sdist.
- **Impact:** Registry or packaging regressions in the other templates could escape artifact-level testing.
- **Fix:** Wheel and sdist jobs now import ForgePy, exercise help/version, generate all seven templates, and compile every generated project.
- **Verification:** The same checks passed locally in fresh wheel and sdist environments outside the checkout.

### Quality gates were inconsistent

- **Problem:** Normal CI omitted `ruff format --check`, although the publishing workflow required it, and Python 3.12 was absent from the cross-platform matrix.
- **Impact:** Formatting could fail only at release time, and the locally available/intermediate supported Python version lacked matrix coverage.
- **Fix:** Added the formatting gate and Python 3.12 to the Linux, macOS, and Windows matrix.
- **Verification:** Local Ruff lint and formatting checks pass; remote matrix execution remains a post-merge prerequisite.

### PyPI and release guidance was incomplete

- **Problem:** The README still described GitHub installation as the intended source, and there was no OIDC TestPyPI rehearsal workflow.
- **Impact:** The PyPI project page would show outdated installation instructions, and pre-release rehearsal could encourage token-based uploads.
- **Fix:** Updated installation guidance, added current name-status caveats, and added an owner-controlled TestPyPI Trusted Publishing workflow.
- **Verification:** Twine successfully rendered the README; workflow configuration was reviewed against current PyPI and GitHub OIDC guidance.

### Generated FastAPI test dependency reviewed

- **Finding:** `httpx2` initially looked unusual but is intentional in the current ecosystem. Starlette 1.7 emits a deprecation warning when used with legacy `httpx` and requests `httpx2` instead.
- **Action:** Retained `httpx2`; no compatibility change was made.
- **Verification:** A freshly generated FastAPI project installed `httpx2` 2.13.1 and its three starter tests passed.

## C. Validation results

| Check | Result | Actual outcome |
|---|---|---|
| Ruff lint | PASS | `python -m ruff check .` |
| Ruff formatting | PASS | `python -m ruff format --check .` |
| Pytest | PASS | 103 tests passed on CPython 3.12.10 / Windows |
| Package build | PASS | Built `forgepy-1.0.0-py3-none-any.whl` and `forgepy-1.0.0.tar.gz` |
| Twine validation | PASS | Both artifacts passed |
| Archive inspection | PASS | Required modules, metadata, license, entry point, rebuild files, and exclusions validated |
| Wheel installation | PASS | Fresh environment outside checkout; import, help, version, seven templates, and compilation passed |
| Source-distribution installation | PASS | Fresh environment outside checkout; import, help, version, seven templates, and compilation passed |
| CLI smoke tests | PASS | `forgepy --help`, `forgepy --version`, imports, valid/invalid arguments, prompts, cancellation, setup errors |
| Template generation | PASS | FastAPI, RAG, Agent, LangGraph, ML, Data Science, and CLI generated and compiled from both artifact types |
| Generated FastAPI execution | PASS | Dependency installation plus 3 generated tests passed with current dependencies |
| Dependency advisory audit | PASS with note | No known vulnerabilities found outside the environment's old `pip` installer; ForgePy itself is not yet on PyPI and was skipped as a project |
| PyPI exact-name lookup | INCONCLUSIVE | Official JSON endpoint returned HTTP 404 on 2026-10-12; absence does not establish availability or reservation eligibility |
| Local cross-platform/version execution | NOT RUN | Only Windows and CPython 3.12.10 were available locally |
| Configured CI coverage | PENDING | Linux, macOS, Windows on Python 3.11, 3.12, and 3.13; must pass after push/PR |
| Live provider/store integrations | NOT RUN | Hosted AI APIs and PostgreSQL were intentionally not contacted; deterministic generation and provider/store composition tests passed |

## D. Files changed

- `pyproject.toml`: PEP 639-compatible licensing, Hatchling floor, OS classifier, changelog URL, Twine dev dependency, validation script in sdist.
- `scripts/validate_dist.py`: wheel/sdist content and metadata validation.
- `tests/test_package_metadata.py`: project metadata and installed entry-point regression tests.
- `.github/workflows/ci.yml`: formatting, full supported Python matrix, archive checks, and all-template artifact smoke tests.
- `.github/workflows/publish.yml`: archive inspection and built-wheel smoke test before OIDC publication.
- `.github/workflows/test-publish.yml`: deliberate, protected TestPyPI OIDC rehearsal.
- `README.md`, `RELEASING.md`, `CONTRIBUTING.md`, `CHANGELOG.md`: accurate installation, validation, and release instructions.

## E. Remaining risks and prerequisites

- Configure the `pypi` and optional `testpypi` GitHub environments with required reviewers and restrictive deployment rules.
- Configure matching pending Trusted Publishers in PyPI/TestPyPI. Exact owner, repository, workflow, and environment names must match.
- Confirm the `forgepy` distribution name in the PyPI account UI. A 404 response does not reserve it; the name may be prohibited or retained.
- Run the configured GitHub Actions matrix. Local execution did not cover Linux, macOS, Python 3.11, or Python 3.13.
- Hosted OpenAI/Groq services, Ollama, pgvector/PostgreSQL, Chroma, and FAISS were not exercised live. Automated tests avoid credentials and external services by design.
- Generated ML/Data Science dependency installation and workload execution were not repeated in this audit; their generated metadata and Python syntax were validated, and template logic is covered by tests.
- The advisory scan reported vulnerabilities in the machine's `pip` 25.0.1 installer. `pip` is not a ForgePy dependency; update the release workstation's installer before future local release work.

## F. Publication instructions

1. Review the working tree and run the final gates:

   ```console
   git diff --check
   python -m pip install -e ".[dev]"
   python -m ruff check .
   python -m ruff format --check .
   python -m pytest
   python -m build
   python -m twine check dist/*
   python scripts/validate_dist.py dist/*
   ```

2. Push the reviewed changes through a pull request and require the full CI workflow to pass. Do not publish artifacts built before the final commit.

3. In GitHub, create a protected environment named `pypi`. In PyPI, create a pending Trusted Publisher for owner `CodeCatalystHadeed`, repository `forgepy`, workflow `publish.yml`, environment `pypi`. Confirm that PyPI accepts the exact distribution name.

4. Optionally rehearse with TestPyPI: create a protected `testpypi` environment and a TestPyPI pending publisher for workflow `test-publish.yml`, dispatch **Publish to TestPyPI**, then run:

   ```console
   python -m pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ forgepy==1.0.0
   forgepy --help
   forgepy --version
   ```

5. After CI passes, create and push annotated tag `v1.0.0`, then publish a GitHub Release for that exact tag. The protected **Publish to PyPI** workflow rebuilds, retests, validates, and publishes through OIDC only after environment approval.

6. Verify the published files, hashes, metadata, provenance, and project links on PyPI. Install into a new environment and smoke-test:

   ```console
   python -m venv verify-forgepy
   # Activate the environment for the current platform.
   python -m pip install forgepy==1.0.0
   python -c "import forgepy; print(forgepy.__version__)"
   forgepy --help
   forgepy --version
   forgepy create release-smoke --template cli --no-interactive
   ```
