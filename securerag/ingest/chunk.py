"""Paragraph-aware chunker with trust and role tags."""

import re

# No tokenizer dependency at ingest time; ~0.75 words per token is a close English approximation.
WORDS_PER_TOKEN = 0.75
MIN_TAIL_WORDS = 30


def chunk_text(text: str, chunk_tokens: int = 300) -> list[str]:
    max_words = int(chunk_tokens * WORDS_PER_TOKEN)
    chunks: list[str] = []
    current: list[str] = []
    count = 0
    for para in re.split(r"\n\s*\n", text):
        words = para.split()
        # A single paragraph longer than the limit is cut on word boundaries.
        for i in range(0, len(words), max_words):
            piece = words[i : i + max_words]
            if count + len(piece) > max_words and current:
                chunks.append("\n\n".join(current))
                current, count = [], 0
            current.append(" ".join(piece))
            count += len(piece)
    if current:
        tail = "\n\n".join(current)
        # A tiny remainder makes a useless retrieval unit, so fold it into the previous chunk.
        if (
            chunks
            and count < MIN_TAIL_WORDS
            and len(chunks[-1].split()) + count <= max_words * 1.25
        ):
            chunks[-1] += "\n\n" + tail
        else:
            chunks.append(tail)
    return chunks


def make_chunks(
    doc_id: str,
    url: str,
    title: str,
    text: str,
    chunk_tokens: int = 300,
    trust: str = "official",
    role: str = "public",
) -> list[dict]:
    return [
        {
            "chunk_id": f"{doc_id}#{i}",
            "doc_id": doc_id,
            "source": url,
            "title": title,
            "text": t,
            "trust": trust,
            "role": role,
        }
        for i, t in enumerate(chunk_text(text, chunk_tokens))
    ]
