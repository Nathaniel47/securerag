# CLAUDE.md: SecureRAG coding rules

- Follow PLAN.md; if anything conflicts, PLAN.md wins. Work one BUILD_STEPS.md step at a time.
- Python 3.11, no LangChain/LlamaIndex. Keep the pipeline plain and each defense a separate hook.
- Secrets only from environment variables named `SECURERAG_*`. Never commit `.env`; `.env.example` has names with empty values.
- All attacks target this app only. Leakage tests use synthetic records, never real personal data.
- Scoring is automatic (success markers, normalised match). No LLM judge.
- Every LLM call goes through the cached client in `securerag/llm/`. Fixed seeds; record model IDs, temperature, seed and git commit in `results/run_meta.json`.
- Format and lint with ruff (line length 100). Write tests in `tests/` for every feature; run `pytest` before each commit.
- Code comments only for non-obvious reasons. Plain-English explanations go in LEARNING.md, not chat.
- Commit with the step name in the message, then push.
