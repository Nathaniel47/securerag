"""The plain RAG pipeline: retrieve, generate, with a hook for each defense at each stage."""

import time
from dataclasses import dataclass, field

from securerag.config import Config
from securerag.defenses.base import Defense
from securerag.llm.client import LLMClient
from securerag.rag.prompt import SYSTEM, build_prompt
from securerag.rag.store import VectorStore


@dataclass
class Trace:
    question: str
    retrieved: list[dict] = field(default_factory=list)  # straight from the vector store
    chunks: list[dict] = field(default_factory=list)  # what the generator actually saw
    answer: str = ""
    blocked: bool = False
    fired: dict[str, str] = field(default_factory=dict)  # defense name -> what it did
    llm_calls: int = 0  # answer-model calls
    guard_calls: int = 0  # Prompt Guard calls (separate quota)
    latency_s: float = 0.0

    def flag(self, defense: str, note: str) -> None:
        self.fired[defense] = note


class Pipeline:
    def __init__(
        self,
        store: VectorStore,
        llm: LLMClient,
        cfg: Config,
        defenses: list[Defense] | None = None,
    ):
        self.store, self.llm, self.cfg = store, llm, cfg
        self.defenses = defenses or []

    def complete(self, trace: Trace, prompt: str, system: str | None, repeat: int) -> str:
        """Every answer-model call goes through here so the trace counts them."""
        trace.llm_calls += 1
        return self.llm.complete(prompt, system=system, repeat=repeat)

    def generate(self, question: str, chunks: list[dict], trace: Trace, repeat: int = 0) -> str:
        prompt = build_prompt(question, chunks, self.cfg)
        return self.complete(trace, prompt, SYSTEM, repeat).strip()

    def ingest(self, chunks: list[dict]) -> list[dict]:
        """Add documents unless an ingest-time defense rejects them. Returns those accepted."""
        accepted = [c for c in chunks if all(d.accepts_document(c) for d in self.defenses)]
        self.store.add(accepted)
        return accepted

    def remove(self, chunk_ids: list[str]) -> None:
        self.store.delete(chunk_ids)

    def ask(self, question: str, repeat: int = 0) -> Trace:
        start = time.perf_counter()
        trace = Trace(question)
        try:
            self._run(question, trace, repeat)
        finally:
            trace.latency_s = time.perf_counter() - start
        return trace

    def _run(self, question: str, trace: Trace, repeat: int) -> None:
        for d in self.defenses:
            refusal = d.check_query(question, trace)
            if refusal is not None:
                trace.blocked, trace.answer = True, refusal
                return
        allowed: frozenset[str] | None = None
        for d in self.defenses:
            if d.allowed_trust is not None:
                allowed = d.allowed_trust if allowed is None else allowed & d.allowed_trust
        trace.retrieved = self.store.query(question, self.cfg.top_k, allowed)
        chunks = trace.retrieved
        for d in self.defenses:
            chunks = d.filter_chunks(question, chunks, trace)
        trace.chunks = chunks
        answer = None
        for d in self.defenses:
            answer = d.generate(self, question, chunks, trace, repeat)
            if answer is not None:
                break
        if answer is None:
            answer = self.generate(question, chunks, trace, repeat)
        for d in self.defenses:
            answer = d.filter_answer(answer, trace)
        trace.answer = answer
