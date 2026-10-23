"""Dense embedding backends.

* ``OpenAICompatibleEmbedder`` — any server exposing ``POST /v1/embeddings`` (Ollama with
  ``bge-m3``, vLLM serving an embedding model, NVIDIA NIM). This is what runs on the GB10.
* ``HashingEmbedder`` — deterministic, dependency-free fallback used in tests and when no
  embedding server is configured. Retrieval then relies mostly on the BM25 sparse channel.
"""

from __future__ import annotations

import math
from typing import Protocol

import httpx
import numpy as np

from .tokenize import token_id, tokenize


class Embedder(Protocol):
    dim: int
    name: str

    def embed(self, texts: list[str]) -> list[list[float]]: ...


class HashingEmbedder:
    name = "hashing-fallback"

    def __init__(self, dim: int = 384) -> None:
        self.dim = dim

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for t in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            toks = tokenize(t)
            for tok in toks:
                rng = np.random.default_rng(token_id(tok))
                vec += rng.standard_normal(self.dim, dtype=np.float32)
            norm = float(np.linalg.norm(vec))
            if norm > 0:
                vec /= norm
            out.append(vec.tolist())
        return out


class OpenAICompatibleEmbedder:
    def __init__(
        self,
        base_url: str,
        model: str,
        *,
        dim: int,
        api_key: str | None = None,
        batch_size: int = 32,
        timeout: float = 120.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.dim = dim
        self.name = f"{model}@{self.base_url}"
        self.batch_size = batch_size
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        self._client = client or httpx.Client(timeout=timeout, headers=headers)

    def embed(self, texts: list[str]) -> list[list[float]]:
        out: list[list[float]] = []
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i : i + self.batch_size]
            resp = self._client.post(
                f"{self.base_url}/embeddings", json={"model": self.model, "input": batch}
            )
            resp.raise_for_status()
            data = sorted(resp.json()["data"], key=lambda d: d.get("index", 0))
            for d in data:
                vec = d["embedding"]
                if len(vec) != self.dim:
                    raise ValueError(
                        f"embedding dimension {len(vec)} != configured EMBEDDINGS_DIM {self.dim}"
                    )
                out.append(vec)
        return out


def embedder_from_env(env: dict[str, str]) -> Embedder:
    base = env.get("EMBEDDINGS_BASE_URL", "").strip()
    if not base:
        return HashingEmbedder(dim=int(env.get("EMBEDDINGS_DIM", "384")))
    return OpenAICompatibleEmbedder(
        base,
        env.get("EMBEDDINGS_MODEL", "bge-m3"),
        dim=int(env.get("EMBEDDINGS_DIM", "1024")),
        api_key=env.get("EMBEDDINGS_API_KEY") or env.get("LLM_API_KEY"),
    )


def cosine(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b, strict=True))
    den = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return num / den if den else 0.0
