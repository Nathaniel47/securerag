"""Load the chunked corpus and build the vector store, caching embeddings on disk."""

import json
from pathlib import Path

import numpy as np

from securerag.rag.embed import Embedder
from securerag.rag.store import VectorStore


def load_chunks(data_dir: Path = Path("data")) -> list[dict]:
    lines = (data_dir / "chunks.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def embed_cached(chunks: list[dict], embedder: Embedder, cache: Path | None) -> np.ndarray:
    ids = np.array([c["chunk_id"] for c in chunks])
    if cache is not None and cache.exists():
        saved = np.load(cache, allow_pickle=False)
        if str(saved["model"]) == embedder.name and np.array_equal(saved["ids"], ids):
            return saved["vectors"]
    vectors = embedder.encode([c["text"] for c in chunks])
    if cache is not None:
        cache.parent.mkdir(parents=True, exist_ok=True)
        np.savez(cache, ids=ids, vectors=vectors, model=embedder.name)
    return vectors


def build_store(
    embedder: Embedder, data_dir: Path = Path("data"), cache: Path | None = None
) -> VectorStore:
    chunks = load_chunks(data_dir)
    store = VectorStore(embedder)
    store.add(chunks, embed_cached(chunks, embedder, cache))
    return store
