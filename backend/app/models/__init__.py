from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..core.db import Base


class Subreddit(Base):
    __tablename__ = "subreddits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), unique=True, index=True)

    score: Mapped[float] = mapped_column(Float, default=0.0)
    mention_count: Mapped[int] = mapped_column(Integer, default=0)
    avg_engagement: Mapped[float] = mapped_column(Float, default=0.0)

    subscribers: Mapped[int] = mapped_column(Integer, default=0)
    active_user_count: Mapped[int] = mapped_column(Integer, default=0)
    topic_relevance: Mapped[int] = mapped_column(Integer, default=0)  # 0/1

    public_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class AnalysisContext(Base):
    __tablename__ = "analysis_context"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_name: Mapped[str] = mapped_column(String(256))
    company_aliases: Mapped[list[str]] = mapped_column(JSON, default=list)
    competitors: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    kind: Mapped[str] = mapped_column(String(16))  # post|comment
    subreddit: Mapped[str] = mapped_column(String(128), index=True)
    author: Mapped[str | None] = mapped_column(String(128), nullable=True)

    text: Mapped[str] = mapped_column(Text)
    url: Mapped[str | None] = mapped_column(Text, nullable=True)
    permalink: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_utc: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[int | None] = mapped_column(Integer, nullable=True)

    parent_source_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("sources.id"), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    mentions: Mapped[list["Mention"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )
    relationships: Mapped[list["Relationship"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(256), unique=True, index=True)
    entity_type: Mapped[str | None] = mapped_column(String(64), nullable=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    mentions: Mapped[list["Mention"]] = relationship(
        back_populates="entity", cascade="all, delete-orphan"
    )
    outgoing_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.subject_entity_id",
        back_populates="subject_entity",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["Relationship"]] = relationship(
        foreign_keys="Relationship.object_entity_id",
        back_populates="object_entity",
        cascade="all, delete-orphan",
    )


class Mention(Base):
    __tablename__ = "mentions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_id: Mapped[int] = mapped_column(Integer, ForeignKey("entities.id"), index=True)
    source_id: Mapped[str] = mapped_column(String(32), ForeignKey("sources.id"), index=True)

    surface_form: Mapped[str] = mapped_column(String(256))
    snippet: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    entity: Mapped[Entity] = relationship(back_populates="mentions")
    source: Mapped[Source] = relationship(back_populates="mentions")


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subject_entity_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("entities.id"), index=True
    )
    object_entity_id: Mapped[int] = mapped_column(Integer, ForeignKey("entities.id"), index=True)
    relationship_type: Mapped[str] = mapped_column(String(64), index=True)

    source_id: Mapped[str | None] = mapped_column(
        String(32), ForeignKey("sources.id"), nullable=True, index=True
    )
    evidence: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    subject_entity: Mapped[Entity] = relationship(
        foreign_keys=[subject_entity_id], back_populates="outgoing_relationships"
    )
    object_entity: Mapped[Entity] = relationship(
        foreign_keys=[object_entity_id], back_populates="incoming_relationships"
    )
    source: Mapped[Source | None] = relationship(back_populates="relationships")
