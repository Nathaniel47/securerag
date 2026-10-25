"""FastAPI backend: ask a question under chosen defenses, replay an attack, read the results.

Run: uvicorn api.main:app
Live questions use the Groq quota, so they are capped per UTC day (SECURERAG_DAILY_LIVE_LIMIT).
"""

import os
import uuid
from collections import OrderedDict
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from securerag.attacks.base import Attack
from securerag.attacks.run import run_attack
from securerag.config import CONFIGS, DEFENSES, Config
from securerag.defenses import build_defenses
from securerag.eval.metrics import summarize
from securerag.eval.run_eval import load_records
from securerag.llm.client import LLMClient
from securerag.rag.pipeline import Pipeline, Trace
from securerag.rag.store import VectorStore

MAX_TRACES = 200
RESULTS = Path("results/runs/full.jsonl")


class AskRequest(BaseModel):
    question: str
    defenses: list[str] = []


class AttackRequest(BaseModel):
    attack_id: str
    defenses: list[str] = []


def trace_json(trace: Trace, trace_id: str) -> dict:
    return {
        "trace_id": trace_id,
        "question": trace.question,
        "answer": trace.answer,
        "blocked": trace.blocked,
        "fired": trace.fired,
        "llm_calls": trace.llm_calls,
        "guard_calls": trace.guard_calls,
        "retrieved": [
            {k: c[k] for k in ("chunk_id", "title", "trust", "score", "text")}
            for c in trace.retrieved
        ],
        "used_chunk_ids": [c["chunk_id"] for c in trace.chunks],
    }


def create_app(
    store: VectorStore,
    llm: LLMClient,
    guard: LLMClient | None = None,
    attacks: list[Attack] | None = None,
    results_path: Path = RESULTS,
    daily_limit: int | None = None,
) -> FastAPI:
    app = FastAPI(title="SecureRAG")
    cfg = Config()
    by_id = {a.id: a for a in attacks or []}
    traces: OrderedDict[str, dict] = OrderedDict()
    limit = (
        daily_limit
        if daily_limit is not None
        else int(os.environ.get("SECURERAG_DAILY_LIVE_LIMIT", "50"))
    )
    used = {"day": "", "n": 0}

    def pipeline(names: list[str]) -> Pipeline:
        unknown = set(names) - set(DEFENSES)
        if unknown:
            raise HTTPException(422, f"unknown defenses: {sorted(unknown)}")
        c = cfg.with_defenses(*names)
        if "d5_prompt_guard" in names and guard is None:
            raise HTTPException(503, "Prompt Guard is not configured")
        return Pipeline(store, llm, c, build_defenses(c, guard))

    def spend() -> None:
        today = datetime.now(UTC).strftime("%Y-%m-%d")
        if used["day"] != today:
            used.update(day=today, n=0)
        if used["n"] >= limit:
            raise HTTPException(429, "Daily live-question limit reached; see the dashboard.")
        used["n"] += 1

    def keep(trace: Trace, extra: dict | None = None) -> dict:
        tid = uuid.uuid4().hex[:12]
        out = {**trace_json(trace, tid), **(extra or {})}
        traces[tid] = out
        while len(traces) > MAX_TRACES:
            traces.popitem(last=False)
        return out

    @app.get("/health")
    def health() -> dict:
        return {"ok": True, "chunks": len(store), "configs": list(CONFIGS)}

    @app.get("/attacks")
    def list_attacks() -> list[dict]:
        return [{"id": a.id, "kind": a.kind, "channel": a.channel, "query": a.query}
                for a in by_id.values()]  # fmt: skip

    @app.post("/ask")
    def ask(req: AskRequest) -> dict:
        pipe = pipeline(req.defenses)
        spend()
        return keep(pipe.ask(req.question))

    @app.post("/attack")
    def attack(req: AttackRequest) -> dict:
        if req.attack_id not in by_id:
            raise HTTPException(404, "unknown attack")
        pipe = pipeline(req.defenses)
        spend()
        trace, ok = run_attack(pipe, by_id[req.attack_id])
        return keep(trace, {"attack_id": req.attack_id, "attack_succeeded": ok})

    @app.get("/trace/{trace_id}")
    def get_trace(trace_id: str) -> dict:
        if trace_id not in traces:
            raise HTTPException(404, "unknown or expired trace")
        return traces[trace_id]

    @app.get("/results")
    def results() -> dict:
        return summarize(load_records(results_path))

    return app
