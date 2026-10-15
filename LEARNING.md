# LEARNING.md

Plain-English notes on what was built and why it matters.

## Step 2: Repo setup

- **Package layout** (`securerag/`, `api/`, `ui/`, `tests/`): mirrors PLAN.md so each part of the pipeline (ingest, retrieval, attacks, defenses, evaluation) has one obvious home. Empty packages are placeholders for later steps.
- **`config.py`**: one place for the defense on/off switches and retrieval settings. `CONFIGS` lists the 6 configurations that will be evaluated (no defense, each of four alone, all combined). Keeping this central means every experiment is described by a config you can save and reproduce.
- **Secrets**: keys come only from `SECURERAG_*` environment variables. `.env` is git-ignored and `.env.example` has names only. The pre-commit hook runs **gitleaks**, which scans each commit for key-like strings and blocks it. Why it matters: free-tier API keys leaked to GitHub get scraped within minutes. Reading: the gitleaks README (pre-commit section).
- **Pre-commit + ruff + CI**: ruff formats and lints; GitHub Actions re-runs lint and tests on every push so a broken commit is visible straight away.
- **Docker**: `docker-compose.yml` defines api, ui and an optional Ollama profile, with memory caps inside the 8 GB budget. The api/ui entry points (`api/main.py`, `ui/playground.py`) are built in step 5, so compose won't start until then.
- **Two requirements files**: `requirements.txt` is the app (heavy: Chroma, sentence-transformers); `requirements-dev.txt` is lint/test tools. CI installs only the dev file for now to stay fast; add runtime packages to CI when tests need them.

How to check: `pytest` and `ruff check .` should both pass.
