"""On-disk response cache. One JSON file per request, keyed by a hash of everything that matters."""

import hashlib
import json
from pathlib import Path

DEFAULT_DIR = Path("llm_cache")


def cache_key(
    model: str,
    messages: list[dict],
    temperature: float | None,
    seed: int | None,
    repeat: int,
    settings: dict | None = None,
) -> str:
    payload = json.dumps(
        [model, messages, temperature, seed, repeat, settings or {}],
        sort_keys=True,
        ensure_ascii=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


class ResponseCache:
    def __init__(self, directory: Path = DEFAULT_DIR):
        self.dir = directory

    def get(self, key: str) -> str | None:
        path = self.dir / f"{key}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))["text"]

    def put(self, key: str, text: str) -> None:
        self.dir.mkdir(parents=True, exist_ok=True)
        (self.dir / f"{key}.json").write_text(json.dumps({"text": text}), encoding="utf-8")
