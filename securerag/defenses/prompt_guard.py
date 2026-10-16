"""D5: scan the question and the retrieved chunks with Llama Prompt Guard 2 (86M).

The model returns a probability-like score in [0, 1] as plain text. Inputs beyond its 512-token
window are cut, which is safe here because chunks are already trimmed before they reach the
answer prompt.
"""

from dataclasses import dataclass, field

from securerag.llm.client import LLMClient

MAX_CHARS = 1800  # ~450 tokens, under the model's 512-token window


@dataclass
class GuardResult:
    query_score: float
    chunk_scores: dict[str, float] = field(default_factory=dict)
    threshold: float = 0.5

    @property
    def query_blocked(self) -> bool:
        return self.query_score >= self.threshold

    @property
    def flagged_chunk_ids(self) -> list[str]:
        return [cid for cid, s in self.chunk_scores.items() if s >= self.threshold]


def score(client: LLMClient, text: str) -> float:
    reply = client.complete(text[:MAX_CHARS]).strip()
    try:
        value = float(reply)
    except ValueError:
        # Unknown output must not pass silently as "safe".
        raise ValueError(f"unexpected Prompt Guard output: {reply!r}") from None
    return min(1.0, max(0.0, value))


def scan(client: LLMClient, query: str, chunks: list[dict], threshold: float = 0.5) -> GuardResult:
    return GuardResult(
        query_score=score(client, query),
        chunk_scores={c["chunk_id"]: score(client, c["text"]) for c in chunks},
        threshold=threshold,
    )


def apply(result: GuardResult, chunks: list[dict]) -> list[dict] | None:
    """Return the chunks that survive, or None when the question itself is blocked."""
    if result.query_blocked:
        return None
    bad = set(result.flagged_chunk_ids)
    return [c for c in chunks if c["chunk_id"] not in bad]
