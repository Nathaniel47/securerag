"""Run one attack attempt against a pipeline: inject, ask, score, clean up."""

from securerag.attacks.base import Attack, succeeded
from securerag.rag.pipeline import Pipeline, Trace


def run_attack(pipe: Pipeline, attack: Attack, repeat: int = 0) -> tuple[Trace, bool]:
    """Documents exist in the knowledge base only for this attempt, so attempts never interact."""
    accepted = pipe.ingest(list(attack.docs))
    try:
        trace = pipe.ask(attack.query, repeat=repeat)
    finally:
        pipe.remove([c["chunk_id"] for c in accepted])
    if len(accepted) < len(attack.docs):
        trace.flag("ingest_scan", f"{len(attack.docs) - len(accepted)} document(s) rejected")
    return trace, succeeded(attack, trace.answer)
