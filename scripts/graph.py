"""Build a sparse weighted graph over articles.

An edge captures the different ways two articles can be related: through what
they're literally about (semantic similarity, named-entity overlap), through
when they happened (temporal proximity), and — the substantive ingredient
here — through which latent forces they activate (source-vector cosine).

The four components are kept separately on each edge so the frontend can
recompute interest and recolour the graph without rebuilding it. The combined
score is used only to prune to a renderable density.
"""

from __future__ import annotations

from datetime import datetime, timezone

import numpy as np

TOP_K_PER_NODE = 15
COMBINED_THRESHOLD = 0.25
TEMPORAL_SCALE_HOURS = 36.0


def hours_since_epoch(dt_string: str) -> float:
    instant = datetime.fromisoformat(dt_string.replace("Z", "+00:00"))
    if instant.tzinfo is None:
        instant = instant.replace(tzinfo=timezone.utc)
    return instant.timestamp() / 3600.0


def _entity_jaccard(left: list[dict], right: list[dict]) -> float:
    left_uris = {c["uri"] for c in left}
    right_uris = {c["uri"] for c in right}
    if not left_uris or not right_uris:
        return 0.0
    return len(left_uris & right_uris) / len(left_uris | right_uris)


def build_graph(articles: list[dict], embeddings: np.ndarray, sources: np.ndarray) -> dict:
    n = len(articles)

    semantic = embeddings @ embeddings.T
    np.fill_diagonal(semantic, 0.0)

    source_normed = sources / (np.linalg.norm(sources, axis=1, keepdims=True) + 1e-9)
    source_cos = source_normed @ source_normed.T
    np.fill_diagonal(source_cos, 0.0)

    times = np.array([hours_since_epoch(a["dateTime"]) for a in articles])
    temporal = np.exp(-np.abs(times[:, None] - times[None, :]) / TEMPORAL_SCALE_HOURS)
    np.fill_diagonal(temporal, 0.0)

    entity = np.zeros((n, n))
    for i in range(n):
        for j in range(i + 1, n):
            entity[i, j] = entity[j, i] = _entity_jaccard(
                articles[i]["concepts"], articles[j]["concepts"]
            )

    combined = 0.4 * semantic + 0.3 * source_cos + 0.2 * entity + 0.1 * temporal

    edges = []
    seen: set[tuple[int, int]] = set()
    for i in range(n):
        candidates = np.argsort(-combined[i])[:TOP_K_PER_NODE]
        for j in candidates:
            if combined[i, j] < COMBINED_THRESHOLD:
                continue
            key = (int(min(i, j)), int(max(i, j)))
            if key in seen:
                continue
            seen.add(key)
            edges.append({
                "source": key[0],
                "target": key[1],
                "weight": round(float(combined[i, j]), 4),
                "semantic": round(float(semantic[i, j]), 4),
                "source_cosine": round(float(source_cos[i, j]), 4),
                "entity_jaccard": round(float(entity[i, j]), 4),
                "temporal": round(float(temporal[i, j]), 4),
            })

    dominant_source = sources.argmax(axis=1)
    source_norm = np.linalg.norm(sources, axis=1)
    max_share = source_norm.max() if source_norm.size else 1.0

    nodes = []
    for i, article in enumerate(articles):
        nodes.append({
            "id": i,
            "uri": article["uri"],
            "title": article["title"],
            "url": article["url"],
            "outlet": article["source"],
            "dateTime": article["dateTime"],
            "category": (article["categories"] or ["general"])[0] or "general",
            "concepts": [c["label"] for c in article["concepts"][:5]],
            "social_score": article["social_score"],
            "sentiment": article["sentiment"],
            "image": article.get("image"),
            "dominant_source": int(dominant_source[i]),
            "source_activations": [round(float(x), 4) for x in sources[i]],
            "source_norm": round(float(source_norm[i] / (max_share + 1e-9)), 4),
        })

    return {"nodes": nodes, "edges": edges}
