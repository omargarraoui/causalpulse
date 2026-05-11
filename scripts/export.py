"""End-to-end pipeline: fetch → embed → fit sources → build graph → write JSON."""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from scripts.embed import embed_articles
from scripts.fetch import fetch_recent_articles
from scripts.graph import build_graph, hours_since_epoch
from scripts.sources import Config, fit_sources

OUTPUT_PATH = Path("data/data.json")
MIN_ARTICLES = 60


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s | %(message)s",
    )
    log = logging.getLogger("export")

    api_key = os.environ.get("NEWSAPI_AI_KEY")
    if not api_key:
        log.error("NEWSAPI_AI_KEY not set")
        return 1

    articles = fetch_recent_articles(api_key)
    if len(articles) < MIN_ARTICLES:
        log.warning("only %d articles, refusing to fit (need at least %d)", len(articles), MIN_ARTICLES)
        return 0

    # Chronological order is required for the GP kernel: the position in the
    # array becomes the time index of each source trajectory.
    articles.sort(key=lambda a: a["dateTime"])

    embeddings = embed_articles(articles)

    times = np.array([hours_since_epoch(a["dateTime"]) for a in articles])
    times -= times.min()

    result = fit_sources(embeddings, times)
    graph = build_graph(articles, embeddings, result["S"])

    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "n_articles": len(articles),
        "n_sources": int(result["S"].shape[1]),
        "length_scales_hours": [round(float(x), 2) for x in result["length_scales"]],
        "nodes": graph["nodes"],
        "edges": graph["edges"],
        "training_history": result["history"],
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(json.dumps(payload, separators=(",", ":")))
    log.info(
        "wrote %s: %d nodes, %d edges, length-scales (hrs) = %s",
        OUTPUT_PATH, len(graph["nodes"]), len(graph["edges"]),
        payload["length_scales_hours"],
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
