"""The single entry point for LLM calls: a cache in front of a pluggable backend."""

from collections.abc import Callable

from securerag.llm.cache import ResponseCache, cache_key

# backend(model, messages, temperature, seed) -> text
Backend = Callable[[str, list[dict], float, int], str]


class LLMClient:
    def __init__(
        self,
        backend: Backend,
        model: str,
        temperature: float,
        seed: int,
        cache: ResponseCache | None = None,
    ):
        self.backend = backend
        self.model = model
        self.temperature = temperature
        self.seed = seed
        self.cache = cache or ResponseCache()
        self.calls = 0
        self.cache_hits = 0

    def complete(self, prompt: str, system: str | None = None, repeat: int = 0) -> str:
        """`repeat` is part of the cache key so repeated runs stay independent."""
        messages = ([{"role": "system", "content": system}] if system else []) + [
            {"role": "user", "content": prompt}
        ]
        key = cache_key(self.model, messages, self.temperature, self.seed, repeat)
        hit = self.cache.get(key)
        if hit is not None:
            self.cache_hits += 1
            return hit
        text = self.backend(self.model, messages, self.temperature, self.seed)
        self.calls += 1
        self.cache.put(key, text)
        return text
