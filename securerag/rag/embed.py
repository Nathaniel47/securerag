"""Embedders. The real one is MiniLM on CPU; the hash embedder keeps tests offline and fast."""

import re
import zlib
from typing import Protocol

import numpy as np


class Embedder(Protocol):
    name: str

    def encode(self, texts: list[str]) -> np.ndarray:
        """Unit-length vectors, one row per text."""


class SentenceTransformerEmbedder:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.name = model_name
        self._model = None

    def encode(self, texts: list[str]) -> np.ndarray:
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.name, device="cpu")
        return np.asarray(
            self._model.encode(
                texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False
            ),
            dtype=np.float32,
        )


class HashEmbedder:
    """Bag-of-words hashing: texts sharing words get similar vectors. Test use only."""

    def __init__(self, dim: int = 256):
        self.name = f"hash-{dim}"
        self.dim = dim

    def encode(self, texts: list[str]) -> np.ndarray:
        out = np.zeros((len(texts), self.dim), dtype=np.float32)
        for i, text in enumerate(texts):
            for word in re.findall(r"[a-z0-9]+", text.lower()):
                out[i, zlib.crc32(word.encode()) % self.dim] += 1.0
        norms = np.linalg.norm(out, axis=1, keepdims=True)
        return out / np.where(norms == 0, 1.0, norms)
