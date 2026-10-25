"""The hook points a defense can use. Each defense overrides only the stages it acts on."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from securerag.rag.pipeline import Pipeline, Trace


class Defense:
    name = "defense"
    # D1 restricts what the retriever may return. None means no restriction.
    allowed_trust: frozenset[str] | None = None

    def accepts_document(self, chunk: dict) -> bool:
        """Ingest-time scan. False keeps the chunk out of the knowledge base."""
        return True

    def check_query(self, question: str, trace: "Trace") -> str | None:
        """Return a refusal message to block the question, or None to let it through."""
        return None

    def filter_chunks(self, question: str, chunks: list[dict], trace: "Trace") -> list[dict]:
        """Drop or reorder retrieved chunks before they reach the generator."""
        return chunks

    def generate(
        self, pipe: "Pipeline", question: str, chunks: list[dict], trace: "Trace", repeat: int
    ) -> str | None:
        """Replace the single answer call (D3). None means the normal generator is used."""
        return None

    def filter_answer(self, answer: str, trace: "Trace") -> str:
        """Post-process the final answer (D4)."""
        return answer
