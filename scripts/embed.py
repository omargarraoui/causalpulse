"""Sentence-transformer embeddings keyed by article URI.

The cache is realigned with the article cache on each call — entries for URIs
no longer present in the article cache are dropped before persisting, so
embedding storage stays bounded along with the article retention window.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

CACHE_PATH = Path("data/embeddings.npz")
MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"

log = logging.getLogger(__name__)


def _key(uri: str) -> str:
    # npz keys must be valid identifiers; raw URIs contain slashes and colons.
    return "u" + hashlib.sha256(uri.encode()).hexdigest()[:24]


def _composite(article: dict) -> str:
    title = article["title"]
    body = article["body"][:400]
    return f"{title}\n\n{body}" if body else title


def embed_articles(articles: list[dict], device: str = "cpu") -> np.ndarray:
    keys = {a["uri"]: _key(a["uri"]) for a in articles}
    expected = set(keys.values())

    cache: dict[str, np.ndarray] = {}
    if CACHE_PATH.exists():
        with np.load(CACHE_PATH, allow_pickle=False) as loaded:
            cache = {k: loaded[k] for k in loaded.files if k in expected}

    missing = [a for a in articles if keys[a["uri"]] not in cache]
    if missing:
        model = SentenceTransformer(MODEL_NAME, device=device)
        vectors = model.encode(
            [_composite(a) for a in missing],
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        for article, vector in zip(missing, vectors):
            cache[keys[article["uri"]]] = vector.astype(np.float32)
        log.info("embed: %d new vectors", len(missing))

    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    np.savez(CACHE_PATH, **cache)

    return np.stack([cache[keys[a["uri"]]] for a in articles])
