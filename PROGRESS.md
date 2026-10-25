# Progress

## Evaluation run (multi-day)

The full run is limited by Groq's 200K tokens per day, so it spans several days. **Daily resume command** (safe to run any time; finished work is skipped, and it pauses itself when the day's budget is used up, then continues after 00:00 UTC):

```powershell
python -m securerag.eval.run_eval --mode full
```

Exit code 75 means "paused for today's budget", not a failure. Results accumulate in `results/runs/full.jsonl`; `python -m securerag.eval.report` rebuilds the tables and charts from whatever is finished.

After the full run: `--mode repeat --repeat 1`, then `2`, then `3`, then `--mode confirm` (needs `SECURERAG_GEMINI_API_KEY`).

## Steps

- [x] Step 2 repo setup, Step 3 data pipeline (question review applied)
- [x] Step 4 core attacks
- [x] Step 5.1 defenses, 5.2 evaluation runner
- [x] Step 5.3 API and UI
- [~] Step 6: tooling, limitations and LEARNING done; results table and charts need the full run to finish
