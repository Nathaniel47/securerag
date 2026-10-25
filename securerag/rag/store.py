"""Chroma vector store: add, remove and query chunks, with an optional trust filter."""

import uuid

import chromadb
import numpy as np

from securerag.rag.embed import Embedder

BATCH = 500
META_FIELDS = ("doc_id", "source", "title", "trust", "role")


class VectorStore:
    def __init__(self, embedder: Embedder):
        self.embedder = embedder
        # A fresh collection name per store keeps tests and attack runs from sharing state,
        # because Chroma's in-memory client is one process-wide singleton.
        self.collection = chromadb.EphemeralClient().create_collection(
            f"kb_{uuid.uuid4().hex}", metadata={"hnsw:space": "cosine"}
        )

    def __len__(self) -> int:
        return self.collection.count()

    def add(self, chunks: list[dict], vectors: np.ndarray | None = None) -> None:
        if not chunks:
            return
        if vectors is None:
            vectors = self.embedder.encode([c["text"] for c in chunks])
        for i in range(0, len(chunks), BATCH):
            part = chunks[i : i + BATCH]
            self.collection.add(
                ids=[c["chunk_id"] for c in part],
                embeddings=vectors[i : i + BATCH].tolist(),
                documents=[c["text"] for c in part],
                metadatas=[{k: c[k] for k in META_FIELDS} for c in part],
            )

    def delete(self, chunk_ids: list[str]) -> None:
        if chunk_ids:
            self.collection.delete(ids=chunk_ids)

    def query(self, text: str, k: int, allowed_trust: frozenset[str] | None = None) -> list[dict]:
        """Top-k chunks by cosine similarity. `score` is the similarity; `embedding` is kept
        because the anomaly defense compares retrieved chunks with each other."""
        where = {"trust": {"$in": sorted(allowed_trust)}} if allowed_trust is not None else None
        vec = self.embedder.encode([text])[0].tolist()
        res = self.collection.query(
            query_embeddings=[vec],
            n_results=max(1, min(k, len(self))),
            where=where,
            include=["documents", "metadatas", "distances", "embeddings"],
        )
        return [
            {
                "chunk_id": cid,
                "text": doc,
                **meta,
                "score": 1.0 - dist,
                "embedding": np.asarray(emb, dtype=np.float32),
            }
            for cid, doc, meta, dist, emb in zip(
                res["ids"][0],
                res["documents"][0],
                res["metadatas"][0],
                res["distances"][0],
                res["embeddings"][0],
                strict=True,
            )
        ]
