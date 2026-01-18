from __future__ import annotations

from math import log10
from typing import Iterable


def _min_max(value: float, min_val: float, max_val: float) -> float:
    if max_val == min_val:
        return 0.5
    return (value - min_val) / (max_val - min_val)


def _safe_log_norm(value: int, max_value: int) -> float:
    if value <= 0 or max_value <= 0:
        return 0.0
    return log10(value) / log10(max_value)


def score_subreddits(items: list[dict]) -> list[dict]:
    if not items:
        return []

    mention_counts = [item.get("mention_count", 0) for item in items]
    avg_engagements = [
        item.get("engagement_sum", 0.0) / max(1, item.get("engagement_count", 1))
        for item in items
    ]
    max_subscribers = max(item.get("subscribers", 0) for item in items)

    min_mentions = min(mention_counts)
    max_mentions = max(mention_counts)
    min_engagement = min(avg_engagements)
    max_engagement = max(avg_engagements)

    for item, avg_engagement in zip(items, avg_engagements):
        mention_norm = _min_max(item.get("mention_count", 0), min_mentions, max_mentions)
        engagement_norm = _min_max(avg_engagement, min_engagement, max_engagement)
        subscriber_norm = _safe_log_norm(item.get("subscribers", 0), max_subscribers)
        topic_relevance = 1.0 if item.get("topic_relevance", 0) else 0.0

        score = (
            mention_norm * 0.35
            + engagement_norm * 0.30
            + subscriber_norm * 0.20
            + topic_relevance * 0.15
        )

        item["avg_engagement"] = avg_engagement
        item["score"] = score

    return items
