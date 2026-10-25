"""The deployed app object: builds the real store and Groq clients on first import."""

from pathlib import Path

from api.main import create_app
from securerag.attacks.build import load_attacks
from securerag.config import Config, load_env
from securerag.llm.groq import groq_client, guard_client
from securerag.rag.embed import SentenceTransformerEmbedder
from securerag.rag.kb import build_store

load_env()
_cfg = Config()
app = create_app(
    build_store(SentenceTransformerEmbedder(_cfg.embedding_model), Path("data"),
                Path("data/embeddings.npz")),
    groq_client(_cfg),
    guard_client(_cfg),
    load_attacks(),
)  # fmt: skip
