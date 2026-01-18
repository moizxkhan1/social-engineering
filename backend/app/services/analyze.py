from __future__ import annotations

import re
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..core.config import settings
from ..models import Entity
from ..repositories import (
    add_mention,
    add_relationship,
    add_source,
    clear_all,
    get_or_create_entity,
    set_analysis_context,
    upsert_subreddit,
)
from .llm import LLMClient
from .proxy import ProxyManager
from .reddit import RedditClient
from .reddit_browser import HybridRedditClient
from .scoring import score_subreddits


ALLOWED_RELATIONSHIPS = [
    "founder",
    "ceo",
    "employee",
    "investor",
    "competitor",
    "parentCompany",
    "subsidiary",
    "partner",
    "acquiredBy",
    "boardMember",
    "advisor",
    "alumniOf",
    "affiliation",
    "critic",
]

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


def _ratio_to_confidence(ratio: float) -> float | None:
    if ratio >= 0.96:
        return 0.9
    if ratio >= 0.92:
        return 0.85
    if ratio >= 0.88:
        return 0.8
    if ratio >= 0.82:
        return 0.7
    return None


def _merge_aliases(name: str, aliases: list[str] | None) -> list[str]:
    merged = [name] + list(aliases or [])
    return [alias.strip() for alias in merged if alias and alias.strip()]


class EntityResolver:
    def __init__(self, db: Session) -> None:
        self._db = db
        self._index: dict[str, int] = {}
        self._load()

    def _load(self) -> None:
        entities = self._db.execute(select(Entity)).scalars().all()
        for entity in entities:
            self._register(entity)

    def _register(self, entity: Entity) -> None:
        names = [entity.canonical_name] + list(entity.aliases or [])
        for name in names:
            key = _normalize_entity_name(name)
            if not key:
                continue
            self._index.setdefault(key, entity.id)

    def _find_match(self, name: str) -> tuple[Entity, float] | None:
        key = _normalize_entity_name(name)
        if not key:
            return None
        entity_id = self._index.get(key)
        if entity_id is not None:
            entity = self._db.get(Entity, entity_id)
            if entity is not None:
                return entity, 1.0

        best_ratio = 0.0
        best_id: int | None = None
        for existing_key, existing_id in self._index.items():
            if len(existing_key) < 3:
                continue
            ratio = SequenceMatcher(None, key, existing_key).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_id = existing_id

        confidence = _ratio_to_confidence(best_ratio)
        if confidence is None or best_id is None:
            return None
        entity = self._db.get(Entity, best_id)
        if entity is None:
            return None
        return entity, confidence

    def resolve(
        self,
        name: str,
        *,
        entity_type: str | None = None,
        aliases: list[str] | None = None,
    ) -> tuple[Entity, float]:
        candidate_names = [name] + list(aliases or [])
        best_entity: Entity | None = None
        best_confidence = 0.0

        for candidate in candidate_names:
            match = self._find_match(candidate)
            if match and match[1] > best_confidence:
                best_entity, best_confidence = match

        merged_aliases = _merge_aliases(name, aliases)
        if best_entity is not None:
            resolved = get_or_create_entity(
                self._db,
                canonical_name=best_entity.canonical_name,
                entity_type=entity_type,
                aliases=merged_aliases,
            )
            self._register(resolved)
            return resolved, best_confidence

        resolved = get_or_create_entity(
            self._db,
            canonical_name=name,
            entity_type=entity_type,
            aliases=merged_aliases,
        )
        self._register(resolved)
        return resolved, 1.0


@dataclass
class CompanyProfile:
    name: str
    aliases: list[str]


def run_analysis(
    db: Session,
    domain: str,
    progress_cb=None,
    proxy_manager: ProxyManager | None = None,
    competitors: list[str] | None = None,
) -> dict:
    clear_all(db)

    if progress_cb:
        progress_cb("resolving_company")

    base_name = _heuristic_company_name(domain)
    llm = LLMClient(api_key=settings.openai_api_key or "", model=settings.openai_model)
    company = llm.resolve_company(domain, base_name)
    aliases = _unique_terms([company.name] + list(company.aliases))
    competitor_names = _normalize_competitors(competitors or [])
    set_analysis_context(
        db,
        company_name=company.name,
        company_aliases=aliases,
        competitors=competitor_names,
    )

    if progress_cb:
        progress_cb("discovering_subreddits")

    # Use hybrid client: browser-based scraping with httpx fallback
    reddit = HybridRedditClient(
        use_browser=settings.browser_enabled,
        headless=settings.browser_headless,
        browser_timeout_ms=settings.browser_timeout_ms,
        min_interval_s=settings.reddit_min_interval_s,
        # httpx fallback options
        client_id=settings.reddit_client_id,
        client_secret=settings.reddit_client_secret,
        username=settings.reddit_username,
        password=settings.reddit_password,
        user_agent=settings.reddit_user_agent,
        proxy_manager=proxy_manager,
    )
    resolver = EntityResolver(db)

    try:
        discovery_terms = _select_terms(aliases, max_terms=3)
        discovery = _discover_subreddits(
            reddit,
            discovery_terms,
            aliases,
            max_pages=settings.max_discovery_pages,
        )
        scored = score_subreddits(discovery)
        scored.sort(key=lambda item: item.get("score", 0.0), reverse=True)

        top20 = scored[:20]
        for item in top20:
            upsert_subreddit(db, item)

        top5 = top20[:5]
        if progress_cb:
            progress_cb("fetching_sources")
        sources = _fetch_sources(
            reddit,
            company.name,
            aliases,
            top5,
            max_posts=settings.max_posts_per_subreddit,
            max_comments=settings.max_comments_per_post,
        )

        for source in sources:
            add_source(db, source)

        sources = [source for source in sources if source.get("text")]
        if settings.max_llm_sources > 0:
            sources = sources[: settings.max_llm_sources]

        if progress_cb:
            progress_cb("llm_extraction")

        source_map = {source["id"]: source for source in sources}
        for batch in _batch(sources, max(1, settings.llm_batch_size)):
            trimmed = [
                {
                    "id": source["id"],
                    "text": source["text"][: settings.max_source_chars],
                }
                for source in batch
            ]
            try:
                extraction = llm.extract_entities_relationships_batch(
                    sources=trimmed,
                    company_name=company.name,
                    aliases=aliases,
                    relationship_types=ALLOWED_RELATIONSHIPS,
                )
            except Exception:
                continue

            for result in extraction.results:
                source = source_map.get(result.source_id)
                if not source:
                    continue

                for entity in result.entities:
                    if entity.confidence < settings.confidence_threshold:
                        continue
                    resolved, resolution_confidence = resolver.resolve(
                        entity.canonical_name,
                        entity_type=entity.entity_type,
                        aliases=entity.aliases,
                    )

                    surface_form = _find_surface_form(
                        source["text"], [entity.canonical_name] + list(entity.aliases)
                    )
                    snippet = (
                        _snippet_for(source["text"], surface_form) if surface_form else None
                    )
                    add_mention(
                        db,
                        entity_id=resolved.id,
                        source_id=source["id"],
                        surface_form=surface_form or entity.canonical_name,
                        snippet=snippet,
                        confidence=min(1.0, entity.confidence * resolution_confidence),
                    )

                for rel in result.relationships:
                    if rel.confidence < settings.confidence_threshold:
                        continue
                    if rel.relationship not in ALLOWED_RELATIONSHIPS:
                        continue

                    subject_entity, _ = resolver.resolve(rel.subject)
                    object_entity, _ = resolver.resolve(rel.object)

                    add_relationship(
                        db,
                        subject_entity_id=subject_entity.id,
                        object_entity_id=object_entity.id,
                        relationship_type=rel.relationship,
                        source_id=source["id"],
                        evidence=rel.evidence,
                        confidence=rel.confidence,
                    )
    finally:
        reddit.close()

    if progress_cb:
        progress_cb("persisting")

    return {
        "status": "complete",
        "company_name": company.name,
        "company_aliases": aliases,
        "competitors": competitor_names,
        "subreddit_count": len(scored),
        "source_count": len(sources),
        "entity_count": _count_entities(db),
        "relationship_count": _count_relationships(db),
    }


def _heuristic_company_name(domain: str) -> str:
    domain = domain.strip()
    if "://" not in domain:
        domain = "https://" + domain
    parsed = urlparse(domain)
    host = parsed.netloc or parsed.path
    host = host.split("@")[-1]
    host = host.split(":")[0]
    parts = [part for part in host.split(".") if part and part.lower() != "www"]
    root = parts[0] if parts else host
    name = " ".join(segment.capitalize() for segment in root.replace("-", " ").split())
    return name or root


def _normalize_competitors(values: list[str]) -> list[str]:
    cleaned_values = []
    for raw in values:
        cleaned = raw.strip()
        if not cleaned:
            continue
        if "://" in cleaned or "." in cleaned:
            cleaned = _heuristic_company_name(cleaned)
        cleaned_values.append(cleaned)

    seen = set()
    result = []
    for val in cleaned_values:
        key = val.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(val)
    return result


def _unique_terms(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for val in values:
        cleaned = val.strip()
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(cleaned)
    return result


def _select_terms(aliases: list[str], max_terms: int) -> list[str]:
    terms = _unique_terms(aliases)
    return terms[:max_terms]


def _discover_subreddits(
    client: RedditClient, terms: list[str], alias_terms: list[str], max_pages: int
) -> list[dict[str, Any]]:
    subreddit_map: dict[str, dict[str, Any]] = {}
    seen_posts: set[str] = set()

    for term in terms:
        after: str | None = None
        for _ in range(max_pages):
            data = client.search_posts(query=term, limit=100, time_filter="month", after=after)
            listing = data.get("data", {})
            children = listing.get("children", [])
            after = listing.get("after")

            for child in children:
                post = child.get("data", {})
                post_id = post.get("name") or post.get("id")
                if not post_id or post_id in seen_posts:
                    continue
                seen_posts.add(post_id)

                subreddit = post.get("subreddit")
                if not subreddit:
                    continue

                entry = subreddit_map.setdefault(
                    subreddit,
                    {
                        "name": subreddit,
                        "mention_count": 0,
                        "engagement_sum": 0.0,
                        "engagement_count": 0,
                    },
                )
                entry["mention_count"] += 1
                score = post.get("score") or 0
                comments = post.get("num_comments") or 0
                entry["engagement_sum"] += float(score + comments)
                entry["engagement_count"] += 1

            if not after:
                break

    subreddit_items = list(subreddit_map.items())
    subreddit_items.sort(
        key=lambda item: (
            item[1].get("mention_count", 0),
            item[1].get("engagement_sum", 0.0),
        ),
        reverse=True,
    )
    if settings.max_discovered_subreddits > 0:
        subreddit_items = subreddit_items[: settings.max_discovered_subreddits]

    # Fetch metadata for discovered subreddits.
    for name, entry in subreddit_items:
        about = client.subreddit_about(name)
        data = about.get("data", {})
        entry["subscribers"] = data.get("subscribers", 0)
        entry["active_user_count"] = data.get("active_user_count", 0)
        entry["public_description"] = data.get("public_description") or ""
        entry["topic_relevance"] = 1 if _matches_topic(entry["public_description"], alias_terms) else 0

    return [entry for _, entry in subreddit_items]


def _fetch_sources(
    client: RedditClient,
    company_name: str,
    aliases: list[str],
    subreddits: list[dict[str, Any]],
    *,
    max_posts: int,
    max_comments: int,
) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = []
    query = _build_query([company_name] + aliases[:4])

    for item in subreddits:
        subreddit = item["name"]
        data = client.subreddit_search_posts(
            subreddit=subreddit,
            query=query,
            limit=max_posts,
            time_filter="month",
            sort="top",
        )
        listing = data.get("data", {})
        children = listing.get("children", [])

        for child in children[:max_posts]:
            post = child.get("data", {})
            post_id = post.get("name") or f"t3_{post.get('id')}"
            text = _post_text(post)
            permalink = post.get("permalink")
            url = (
                f"https://www.reddit.com{permalink}"
                if permalink
                else post.get("url_overridden_by_dest")
            )
            sources.append(
                {
                    "id": post_id,
                    "kind": "post",
                    "subreddit": subreddit,
                    "author": post.get("author"),
                    "text": text,
                    "url": url,
                    "permalink": permalink,
                    "created_utc": post.get("created_utc"),
                    "score": post.get("score"),
                    "parent_source_id": None,
                }
            )

            post_short_id = post.get("id")
            if not post_short_id:
                continue
            comments_payload = client.comments(
                post_id=post_short_id,
                limit=max_comments,
                depth=2,
                sort="top",
            )
            if not isinstance(comments_payload, list) or len(comments_payload) < 2:
                continue
            comment_listing = comments_payload[1].get("data", {})
            comment_children = comment_listing.get("children", [])

            comment_count = 0
            for child_comment in comment_children:
                if comment_count >= max_comments:
                    break
                if child_comment.get("kind") != "t1":
                    continue
                comment = child_comment.get("data", {})
                body = comment.get("body")
                if not body:
                    continue
                comment_id = comment.get("name") or f"t1_{comment.get('id')}"
                comment_permalink = comment.get("permalink") or permalink
                comment_url = (
                    f"https://www.reddit.com{comment_permalink}"
                    if comment_permalink
                    else url
                )
                sources.append(
                    {
                        "id": comment_id,
                        "kind": "comment",
                        "subreddit": subreddit,
                        "author": comment.get("author"),
                        "text": body,
                        "url": comment_url,
                        "permalink": comment_permalink,
                        "created_utc": comment.get("created_utc"),
                        "score": comment.get("score"),
                        "parent_source_id": post_id,
                    }
                )
                comment_count += 1

    return sources


def _post_text(post: dict[str, Any]) -> str:
    title = post.get("title") or ""
    body = post.get("selftext") or ""
    if body:
        return f"{title}\n\n{body}".strip()
    return title


def _build_query(terms: list[str]) -> str:
    cleaned = []
    for term in _unique_terms(terms):
        if " " in term:
            cleaned.append(f"\"{term}\"")
        else:
            cleaned.append(term)
    return " OR ".join(cleaned)


def _matches_topic(description: str, terms: list[str]) -> bool:
    if not description:
        return False
    lowered = description.lower()
    for term in terms:
        cleaned = term.strip().lower()
        if len(cleaned) < 3:
            continue
        if cleaned in lowered:
            return True
    return False


def _find_surface_form(text: str, candidates: list[str]) -> str | None:
    lowered = text.lower()
    for candidate in candidates:
        if not candidate:
            continue
        if candidate.lower() in lowered:
            return candidate
    return None


def _snippet_for(text: str, surface_form: str, window: int = 60) -> str | None:
    if not surface_form:
        return None
    lowered = text.lower()
    idx = lowered.find(surface_form.lower())
    if idx == -1:
        return None
    start = max(0, idx - window)
    end = min(len(text), idx + len(surface_form) + window)
    return text[start:end].strip()


def _batch(values: list[dict[str, Any]], size: int) -> list[list[dict[str, Any]]]:
    if size <= 0:
        return [values]
    return [values[i : i + size] for i in range(0, len(values), size)]


def _count_entities(db: Session) -> int:
    from sqlalchemy import select, func
    from ..models import Entity

    return db.execute(select(func.count(Entity.id))).scalar_one()


def _count_relationships(db: Session) -> int:
    from sqlalchemy import select, func
    from ..models import Relationship

    return db.execute(select(func.count(Relationship.id))).scalar_one()
