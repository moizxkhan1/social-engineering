from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..models import AnalysisContext, Entity, Mention, Relationship, Source, Subreddit


def clear_all(db: Session) -> None:
    db.execute(delete(AnalysisContext))
    db.execute(delete(Relationship))
    db.execute(delete(Mention))
    db.execute(delete(Entity))
    db.execute(delete(Source))
    db.execute(delete(Subreddit))
    db.commit()


def get_or_create_entity(
    db: Session,
    *,
    canonical_name: str,
    entity_type: str | None = None,
    aliases: list[str] | None = None,
) -> Entity:
    existing = db.execute(
        select(Entity).where(Entity.canonical_name == canonical_name)
    ).scalar_one_or_none()
    if existing is not None:
        if entity_type and not existing.entity_type:
            existing.entity_type = entity_type
        if aliases:
            existing_aliases = set(existing.aliases or [])
            merged = list(existing_aliases.union(set(aliases)))
            merged.sort(key=str.lower)
            existing.aliases = merged
        db.add(existing)
        db.commit()
        db.refresh(existing)
        return existing

    entity = Entity(
        canonical_name=canonical_name,
        entity_type=entity_type,
        aliases=sorted(set(aliases or []), key=str.lower),
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def upsert_subreddit(db: Session, payload: dict) -> Subreddit:
    name = payload["name"]
    existing = db.execute(select(Subreddit).where(Subreddit.name == name)).scalar_one_or_none()
    if existing is None:
        existing = Subreddit(name=name)

    existing.score = float(payload.get("score", existing.score or 0.0))
    existing.mention_count = int(payload.get("mention_count", existing.mention_count or 0))
    existing.avg_engagement = float(payload.get("avg_engagement", existing.avg_engagement or 0.0))
    existing.subscribers = int(payload.get("subscribers", existing.subscribers or 0))
    existing.active_user_count = int(
        payload.get("active_user_count", existing.active_user_count or 0)
    )
    existing.topic_relevance = int(payload.get("topic_relevance", existing.topic_relevance or 0))
    existing.public_description = payload.get("public_description", existing.public_description)

    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def add_source(db: Session, payload: dict) -> Source:
    source_id = payload["id"]
    existing = db.get(Source, source_id)
    if existing is not None:
        return existing

    source = Source(
        id=source_id,
        kind=payload["kind"],
        subreddit=payload["subreddit"],
        author=payload.get("author"),
        text=payload["text"],
        url=payload.get("url"),
        permalink=payload.get("permalink"),
        created_utc=payload.get("created_utc"),
        score=payload.get("score"),
        parent_source_id=payload.get("parent_source_id"),
    )
    db.add(source)
    db.commit()
    db.refresh(source)
    return source


def add_mention(
    db: Session,
    *,
    entity_id: int,
    source_id: str,
    surface_form: str,
    snippet: str | None,
    confidence: float,
) -> Mention:
    mention = Mention(
        entity_id=entity_id,
        source_id=source_id,
        surface_form=surface_form,
        snippet=snippet,
        confidence=confidence,
    )
    db.add(mention)
    db.commit()
    db.refresh(mention)
    return mention


def add_relationship(
    db: Session,
    *,
    subject_entity_id: int,
    object_entity_id: int,
    relationship_type: str,
    source_id: str | None,
    evidence: str | None,
    confidence: float,
) -> Relationship:
    relationship = Relationship(
        subject_entity_id=subject_entity_id,
        object_entity_id=object_entity_id,
        relationship_type=relationship_type,
        source_id=source_id,
        evidence=evidence,
        confidence=confidence,
    )
    db.add(relationship)
    db.commit()
    db.refresh(relationship)
    return relationship


def set_analysis_context(
    db: Session,
    *,
    company_name: str,
    company_aliases: list[str],
    competitors: list[str],
) -> AnalysisContext:
    existing = db.get(AnalysisContext, 1)
    if existing is None:
        existing = AnalysisContext(id=1)

    existing.company_name = company_name
    existing.company_aliases = list(company_aliases or [])
    existing.competitors = list(competitors or [])

    db.add(existing)
    db.commit()
    db.refresh(existing)
    return existing


def get_analysis_context(db: Session) -> AnalysisContext | None:
    return db.get(AnalysisContext, 1)
