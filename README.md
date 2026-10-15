# SecureRAG: RAG Security Testbed

A RAG assistant over public GOV.UK guidance, plus a harness that attacks it (knowledge-base poisoning, indirect and direct prompt injection, data leakage), applies four defenses, and scores each defense automatically.

> Status: under construction. See [PLAN.md](PLAN.md) and [BUILD_STEPS.md](BUILD_STEPS.md).

## Run locally

Requires Python 3.11+ (Docker optional). Commands below are for Windows PowerShell; macOS/Linux equivalents are in comments.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1          # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env              # macOS/Linux: cp .env.example .env  (then fill in keys)
pre-commit install                  # enables gitleaks + ruff on every commit
pytest
```

With Docker (api + ui; works once step 5 is built):

```
docker compose up --build
```

## Configuration

Keys are read from environment variables only: `SECURERAG_GROQ_API_KEY`, `SECURERAG_GEMINI_API_KEY`. Never commit `.env`.

## Data licences

Filled in during the data pipeline step. Corpus: GOV.UK guidance under the [Open Government Licence v3](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/).
