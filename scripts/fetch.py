"""Pull recent news through the NewsAPI.ai SDK with a URI-keyed local cache.

The 2k-token monthly budget is the constraint that shapes this module: every
call must add genuinely new articles. The cache (`data/raw/articles.jsonl`) is
loaded before each fetch, articles already present are skipped, and entries
older than the retention window are pruned on write — so the cache stays
bounded and the model always sees a rolling window of recent coverage.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from eventregistry import (
    ArticleInfoFlags,
    ConceptInfoFlags,
    EventRegistry,
    QueryArticlesIter,
    ReturnInfo,
)

CACHE_PATH = Path("data/raw/articles.jsonl")
RETENTION_DAYS = 14
FETCH_WINDOW_DAYS = 2

log = logging.getLogger(__name__)


def _parse_dt(value: str) -> datetime:
    # NewsAPI.ai emits a separate dateTime and dateTimePub; both are ISO 8601
    # but occasionally lack the trailing Z, which fromisoformat used to reject.
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _load_cache() -> dict[str, dict]:
    if not CACHE_PATH.exists():
        return {}
    with CACHE_PATH.open() as f:
        return {entry["uri"]: entry for entry in (json.loads(line) for line in f)}


def _persist(articles: dict[str, dict]) -> None:
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    cutoff = datetime.now(timezone.utc) - timedelta(days=RETENTION_DAYS)
    fresh = {
        uri: article
        for uri, article in articles.items()
        if _parse_dt(article["dateTime"]) >= cutoff
    }
    with CACHE_PATH.open("w") as f:
        for article in fresh.values():
            f.write(json.dumps(article, separators=(",", ":")) + "\n")


def _normalise(raw: dict) -> dict:
    shares = raw.get("shares") if isinstance(raw.get("shares"), dict) else {}
    return {
        "uri": raw["uri"],
        "title": raw.get("title", "").strip(),
        "body": (raw.get("body") or "")[:1500].strip(),
        "url": raw.get("url", ""),
        "source": (raw.get("source") or {}).get("title", "unknown"),
        "dateTime": raw["dateTime"],
        "concepts": [
            {
                "uri": c["uri"],
                "label": (c.get("label") or {}).get("eng", c.get("uri", "").rsplit("/", 1)[-1]),
                "score": c.get("score", 0),
                "type": c.get("type", ""),
            }
            for c in (raw.get("concepts") or [])[:8]
        ],
        "categories": [(c.get("label") or "").split("/")[-1] for c in (raw.get("categories") or [])[:3]],
        "sentiment": raw.get("sentiment"),
        "social_score": sum(v for v in shares.values() if isinstance(v, (int, float))),
        "image": raw.get("image"),
    }


def fetch_recent_articles(api_key: str, max_new: int = 300) -> list[dict]:
    cached = _load_cache()

    er = EventRegistry(apiKey=api_key, allowUseOfArchive=False)
    return_info = ReturnInfo(
        articleInfo=ArticleInfoFlags(
            bodyLen=1500,
            concepts=True,
            categories=True,
            sentiment=True,
            image=True,
            socialScore=True,
        ),
        conceptInfo=ConceptInfoFlags(label=True, type=True),
    )

    since = datetime.now(timezone.utc) - timedelta(days=FETCH_WINDOW_DAYS)
    query = QueryArticlesIter(
        lang="eng",
        dateStart=since.date().isoformat(),
        isDuplicateFilter="skipDuplicates",
        dataType="news",
    )

    added = 0
    # sortBy="socialScore" biases the iterator toward globally salient stories,
    # which is what the user actually consumes — and what makes cross-domain
    # latent forces visible in the first place.
    for raw in query.execQuery(
        er, sortBy="socialScore", maxItems=max_new, returnInfo=return_info
    ):
        if raw["uri"] in cached:
            continue
        cached[raw["uri"]] = _normalise(raw)
        added += 1

    _persist(cached)
    log.info("fetch: %d new, %d total in cache", added, len(cached))
    return list(cached.values())
