from __future__ import annotations

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from sqlalchemy.orm import aliased

from .core.config import settings
from .core.db import SessionLocal, get_db, init_db
from .models import Entity, Mention, Relationship, Source, Subreddit
from .schemas import (
    AnalyzeRequest,
    EntityDetailOut,
    EntityOut,
    EntityRelationshipSummary,
    MentionOut,
    RelationshipOut,
    SubredditOut,
 )
from .services.analyze import run_analysis
from .services.competitive import build_competitive_overview
from .services.jobs import job_manager
from .services.llm import LLMConfigError
from .services.proxy import ProxyManager
from .services.reddit import RedditAuthError, RedditConfigError, RedditRequestError
from .utils.logging import get_logger, setup_logging

logger = get_logger("sie.api")

# Global proxy manager (initialized on startup if enabled)
proxy_manager: ProxyManager | None = None

app = FastAPI(title="Social Intelligence Engine API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def _startup() -> None:
    global proxy_manager
    setup_logging(settings.log_level)
    logger.info("Starting API")
    init_db()

    # Initialize proxy manager if enabled
    if settings.proxy_enabled and (settings.proxy_list_url or settings.proxifly_api_key):
        proxy_manager = ProxyManager(
            proxy_url=settings.proxy_list_url,
            refresh_interval_s=settings.proxy_refresh_interval_s,
            default_scheme=settings.proxy_default_scheme,
            cache_path=settings.proxy_cache_path,
            cache_enabled=settings.proxy_cache_enabled,
            proxifly_api_key=settings.proxifly_api_key,
            proxifly_protocol=settings.proxifly_protocol,
            proxifly_anonymity=settings.proxifly_anonymity,
            proxifly_country=settings.proxifly_country,
            proxifly_https=settings.proxifly_https,
            proxifly_speed_ms=settings.proxifly_speed_ms,
            pool_size=settings.proxy_pool_size,
            proxifly_max_retries=settings.proxifly_max_retries,
            proxifly_min_backoff_s=settings.proxifly_min_backoff_s,
            proxifly_max_backoff_s=settings.proxifly_max_backoff_s,
            proxifly_rate_limit_cooldown_s=settings.proxifly_rate_limit_cooldown_s,
            proxifly_max_wait_s=settings.proxifly_max_wait_s,
        )
        proxy_manager.start_refresh_loop()
        logger.info(
            "Proxy rotation enabled with %d proxies", proxy_manager.proxy_count
        )


@app.on_event("shutdown")
def _shutdown() -> None:
    global proxy_manager
    if proxy_manager is not None:
        proxy_manager.stop()
        proxy_manager = None
        logger.info("Proxy manager stopped")


def _run_job(job_id: str, domain: str, competitors: list[str]) -> None:
    job_manager.start_job(job_id)
    db = SessionLocal()
    try:
        result = run_analysis(
            db,
            domain,
            progress_cb=lambda step: job_manager.update_progress(job_id, step),
            proxy_manager=proxy_manager,
            competitors=competitors,
        )
        job_manager.finish_job(job_id, result=result)
    except LLMConfigError as exc:
        job_manager.fail_job(job_id, str(exc))
    except (RedditConfigError, RedditAuthError, RedditRequestError) as exc:
        job_manager.fail_job(job_id, str(exc))
    except Exception as exc:
        logger.exception("Analysis failed: %s", str(exc))
        job_manager.fail_job(job_id, f"Analysis failed: {exc.__class__.__name__}: {exc}")
    finally:
        db.close()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "environment": settings.environment}


@app.get("/api/proxies")
def proxy_status() -> dict:
    """
    Debug/status endpoint. Does NOT return proxy credentials or full lists.
    """
    enabled = bool(settings.proxy_enabled)
    source = "disabled"
    if enabled:
        if settings.proxifly_api_key:
            source = "proxifly"
        elif settings.proxy_list_url:
            source = "url"
        else:
            source = "misconfigured"

    count = proxy_manager.proxy_count if proxy_manager is not None else 0
    return {"enabled": enabled, "source": source, "count": count}


@app.post("/api/analyze")
def analyze(payload: AnalyzeRequest) -> dict:
    try:
        job = job_manager.create_job(payload.domain, payload.competitors)
    except RuntimeError:
        raise HTTPException(status_code=409, detail="Analysis already running")

    import threading

    threading.Thread(
        target=_run_job,
        args=(job.job_id, payload.domain, payload.competitors),
        daemon=True,
    ).start()
    return {"job_id": job.job_id, "status": job.status}


@app.get("/api/jobs/{job_id}")
def job_status(job_id: str) -> dict:
    job = job_manager.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "job_id": job.job_id,
        "status": job.status,
        "progress": job.progress,
        "error": job.error,
        "result": job.result,
    }


@app.get("/api/subreddits")
def list_subreddits(db: Session = Depends(get_db)) -> list[SubredditOut]:
    rows = db.execute(select(Subreddit).order_by(Subreddit.score.desc())).scalars().all()
    return [
        SubredditOut(
            name=row.name,
            score=row.score,
            mention_count=row.mention_count,
            avg_engagement=row.avg_engagement,
            subscribers=row.subscribers,
            active_user_count=row.active_user_count,
            topic_relevance=row.topic_relevance,
            public_description=row.public_description,
        )
        for row in rows
    ]


@app.get("/api/entities")
def list_entities(db: Session = Depends(get_db)) -> list[EntityOut]:
    stmt = (
        select(Entity, func.count(Mention.id).label("mention_count"))
        .outerjoin(Mention, Mention.entity_id == Entity.id)
        .group_by(Entity.id)
        .order_by(func.count(Mention.id).desc(), Entity.canonical_name.asc())
    )
    rows = db.execute(stmt).all()
    return [
        EntityOut(
            id=entity.id,
            canonical_name=entity.canonical_name,
            aliases=list(entity.aliases or []),
            entity_type=entity.entity_type,
            mention_count=int(mention_count or 0),
        )
        for entity, mention_count in rows
    ]


@app.get("/api/entities/{entity_id}")
def get_entity(entity_id: int, db: Session = Depends(get_db)) -> EntityDetailOut:
    entity = db.get(Entity, entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail="Entity not found")

    mentions_stmt = (
        select(Mention, Source)
        .join(Source, Source.id == Mention.source_id)
        .where(Mention.entity_id == entity_id)
        .order_by(Mention.id.desc())
    )
    mention_rows = db.execute(mentions_stmt).all()
    mentions = [
        MentionOut(
            id=mention.id,
            surface_form=mention.surface_form,
            snippet=mention.snippet,
            source_id=source.id,
            source_url=source.url,
            subreddit=source.subreddit,
            confidence=float(mention.confidence),
        )
        for mention, source in mention_rows
    ]

    rel_stmt = (
        select(
            Relationship.relationship_type,
            Entity.canonical_name,
            func.count(Relationship.id),
        )
        .join(Entity, Entity.id == Relationship.object_entity_id)
        .where(Relationship.subject_entity_id == entity_id)
        .group_by(Relationship.relationship_type, Entity.canonical_name)
        .order_by(func.count(Relationship.id).desc())
    )
    rel_rows = db.execute(rel_stmt).all()
    relationships = [
        EntityRelationshipSummary(type=rel_type, target=target, count=int(count))
        for rel_type, target, count in rel_rows
    ]

    return EntityDetailOut(
        id=entity.id,
        canonical_name=entity.canonical_name,
        aliases=list(entity.aliases or []),
        entity_type=entity.entity_type,
        mentions=mentions,
        relationships=relationships,
    )


@app.get("/api/relationships")
def list_relationships(db: Session = Depends(get_db)) -> list[RelationshipOut]:
    subject = aliased(Entity)
    obj = aliased(Entity)
    stmt = (
        select(Relationship, subject.canonical_name, obj.canonical_name, Source.url)
        .join(subject, subject.id == Relationship.subject_entity_id)
        .join(obj, obj.id == Relationship.object_entity_id)
        .outerjoin(Source, Source.id == Relationship.source_id)
        .order_by(Relationship.id.desc())
    )
    rows = db.execute(stmt).all()
    return [
        RelationshipOut(
            id=rel.id,
            type=rel.relationship_type,
            subject=subject_name,
            object=object_name,
            confidence=float(rel.confidence),
            evidence=rel.evidence,
            source_id=rel.source_id,
            source_url=source_url,
        )
        for rel, subject_name, object_name, source_url in rows
    ]


@app.get("/api/competitive")
def competitive_overview(db: Session = Depends(get_db)) -> dict:
    return build_competitive_overview(db)


@app.get("/api/graph")
def graph(db: Session = Depends(get_db)) -> dict:
    entities = db.execute(select(Entity)).scalars().all()
    relationships = db.execute(select(Relationship)).scalars().all()

    nodes = [
        {"id": entity.id, "name": entity.canonical_name, "type": entity.entity_type}
        for entity in entities
    ]
    edges = [
        {
            "source": rel.subject_entity_id,
            "target": rel.object_entity_id,
            "type": rel.relationship_type,
            "confidence": rel.confidence,
            "source_id": rel.source_id,
        }
        for rel in relationships
    ]
    return {"nodes": nodes, "edges": edges}
