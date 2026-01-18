from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from itertools import combinations
import re
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AnalysisContext, Entity, Mention, Source
from ..repositories import get_analysis_context


_POSITIVE_WORDS = {
    "good",
    "great",
    "excellent",
    "positive",
    "love",
    "loved",
    "like",
    "amazing",
    "awesome",
    "improve",
    "improved",
    "growth",
    "strong",
    "innovative",
    "leader",
    "win",
    "wins",
    "success",
}

_NEGATIVE_WORDS = {
    "bad",
    "poor",
    "terrible",
    "negative",
    "hate",
    "hated",
    "awful",
    "worse",
    "worst",
    "decline",
    "drop",
    "weak",
    "problem",
    "issues",
    "risk",
    "lawsuit",
    "fraud",
    "fail",
    "failed",
}

_ENTITY_STOPWORDS = {
    "a",
    "an",
    "and",
    "company",
    "co",
    "co.",
    "corp",
    "corp.",
    "corporation",
    "inc",
    "inc.",
    "incorporated",
    "llc",
    "ltd",
    "ltd.",
    "limited",
    "the",
}

_ENTITY_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def _normalize_entity_name(value: str) -> str:
    cleaned = value.strip().lower()
    if not cleaned:
        return ""
    if cleaned.startswith("@"):
        cleaned = cleaned[1:]
    cleaned = cleaned.replace("&", "and")
    cleaned = _ENTITY_NORMALIZE_RE.sub(" ", cleaned)
    tokens = [token for token in cleaned.split() if token and token not in _ENTITY_STOPWORDS]
    return "".join(tokens)


def _tokenize(text: str) -> list[str]:
    cleaned = re.sub(r"[^a-z0-9\s]", " ", text.lower())
    return [token for token in cleaned.split() if token]


def _sentiment_score(text: str) -> float:
    tokens = _tokenize(text)
    if not tokens:
        return 0.0
    pos = sum(1 for token in tokens if token in _POSITIVE_WORDS)
    neg = sum(1 for token in tokens if token in _NEGATIVE_WORDS)
    total = pos + neg
    if total == 0:
        return 0.0
    return (pos - neg) / total


def _sentiment_label(score: float) -> str:
    if score >= 0.1:
        return "positive"
    if score <= -0.1:
        return "negative"
    return "neutral"


def _compile_alias_pattern(value: str) -> re.Pattern | None:
    tokens = re.findall(r"[a-z0-9]+", value.lower())
    if not tokens:
        return None
    normalized = "".join(tokens)
    if len(normalized) < 3:
        return None
    pattern = r"\b" + r"[\s\W_]+".join(re.escape(token) for token in tokens) + r"\b"
    return re.compile(pattern, re.IGNORECASE)


def _build_target_patterns(context: AnalysisContext, targets: list[str]) -> dict[str, list[re.Pattern]]:
    patterns: dict[str, list[re.Pattern]] = defaultdict(list)
    for target in targets:
        compiled = _compile_alias_pattern(target)
        if compiled:
            patterns[target].append(compiled)

    for alias in context.company_aliases or []:
        compiled = _compile_alias_pattern(alias)
        if compiled:
            patterns[context.company_name].append(compiled)

    return patterns


def _match_targets_in_text(text: str, patterns: dict[str, list[re.Pattern]]) -> set[str]:
    if not text:
        return set()
    matches: set[str] = set()
    for target, compiled_list in patterns.items():
        for compiled in compiled_list:
            if compiled.search(text):
                matches.add(target)
                break
    return matches


def _build_target_index(context: AnalysisContext) -> tuple[list[str], dict[str, str]]:
    raw_targets = [context.company_name] + list(context.competitors or [])
    seen = set()
    targets = []
    for target in raw_targets:
        key = target.strip().lower()
        if not key or key in seen:
            continue
        seen.add(key)
        targets.append(target)

    alias_map: dict[str, str] = {}

    for target in targets:
        key = _normalize_entity_name(target)
        if key:
            alias_map[key] = target

    for alias in context.company_aliases or []:
        key = _normalize_entity_name(alias)
        if key:
            alias_map[key] = context.company_name

    return targets, alias_map


def _match_target(entity: Entity, alias_map: dict[str, str]) -> str | None:
    key = _normalize_entity_name(entity.canonical_name)
    if key in alias_map:
        return alias_map[key]
    for alias in entity.aliases or []:
        alias_key = _normalize_entity_name(alias)
        if alias_key in alias_map:
            return alias_map[alias_key]
    return None


def build_competitive_overview(db: Session) -> dict[str, Any]:
    context = get_analysis_context(db)
    if context is None:
        return {
            "targets": [],
            "subreddit_share": [],
            "sentiment": [],
            "co_mentions": [],
            "anomalies": [],
        }

    targets, alias_map = _build_target_index(context)

    mention_stmt = (
        select(Mention, Entity, Source)
        .join(Entity, Entity.id == Mention.entity_id)
        .join(Source, Source.id == Mention.source_id)
    )
    rows = db.execute(mention_stmt).all()
    sources = db.execute(select(Source)).scalars().all()

    share_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    sentiment_counts: dict[str, dict[str, int]] = defaultdict(
        lambda: {"positive": 0, "neutral": 0, "negative": 0}
    )
    source_targets: dict[str, set[str]] = defaultdict(set)
    source_sentiment: dict[str, str] = {}
    daily_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for mention, entity, source in rows:
        target = _match_target(entity, alias_map)
        if not target:
            continue
        source_targets[source.id].add(target)

    patterns = _build_target_patterns(context, targets)
    source_index = {source.id: source for source in sources}

    for source_id, source in source_index.items():
        detected = _match_targets_in_text(source.text or "", patterns)
        if detected:
            source_targets[source_id].update(detected)

    for source_id, targets_set in source_targets.items():
        source = source_index.get(source_id)
        if not source:
            continue
        for target in targets_set:
            share_counts[source.subreddit][target] += 1

            if source_id not in source_sentiment:
                score = _sentiment_score(source.text or "")
                source_sentiment[source_id] = _sentiment_label(score)
            sentiment_counts[target][source_sentiment[source_id]] += 1

            if source.created_utc:
                date_key = datetime.fromtimestamp(
                    source.created_utc, tz=timezone.utc
                ).date().isoformat()
                daily_counts[target][date_key] += 1

    subreddit_share = []
    for subreddit, counts in share_counts.items():
        total = sum(counts.values())
        share = {
            target: (counts.get(target, 0) / total if total else 0.0) for target in targets
        }
        subreddit_share.append(
            {
                "subreddit": subreddit,
                "counts": dict(counts),
                "share": share,
                "total": total,
            }
        )

    subreddit_share.sort(key=lambda item: item.get("total", 0), reverse=True)

    sentiment = []
    for target in targets:
        counts = sentiment_counts.get(target, {"positive": 0, "neutral": 0, "negative": 0})
        sentiment.append(
            {
                "target": target,
                "positive": counts["positive"],
                "neutral": counts["neutral"],
                "negative": counts["negative"],
            }
        )

    co_mentions_map: dict[tuple[str, str], int] = defaultdict(int)
    for targets_set in source_targets.values():
        if len(targets_set) < 2:
            continue
        for pair in combinations(sorted(targets_set), 2):
            co_mentions_map[pair] += 1

    co_mentions = [
        {"pair": [pair[0], pair[1]], "count": count}
        for pair, count in co_mentions_map.items()
    ]
    co_mentions.sort(key=lambda item: item["count"], reverse=True)

    anomalies = []
    for target, counts_by_day in daily_counts.items():
        values = list(counts_by_day.values())
        if len(values) < 3:
            continue
        mean = sum(values) / len(values)
        variance = sum((val - mean) ** 2 for val in values) / len(values)
        stdev = variance ** 0.5
        if stdev == 0:
            continue
        for date_key, count in counts_by_day.items():
            z_score = (count - mean) / stdev
            if z_score >= 2.0 and count >= 3:
                anomalies.append(
                    {
                        "target": target,
                        "date": date_key,
                        "count": count,
                        "z_score": round(z_score, 2),
                    }
                )

    anomalies.sort(key=lambda item: item["z_score"], reverse=True)

    return {
        "targets": targets,
        "subreddit_share": subreddit_share,
        "sentiment": sentiment,
        "co_mentions": co_mentions,
        "anomalies": anomalies,
    }
