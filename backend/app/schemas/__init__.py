from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class AnalyzeRequest(BaseModel):
    domain: str = Field(min_length=1, max_length=253)


class SubredditOut(BaseModel):
    name: str
    score: float
    mention_count: int
    avg_engagement: float
    subscribers: int
    active_user_count: int
    topic_relevance: int
    public_description: str | None


class EntityOut(BaseModel):
    id: int
    canonical_name: str
    aliases: list[str]
    entity_type: str | None
    mention_count: int


class MentionOut(BaseModel):
    id: int
    surface_form: str
    snippet: str | None
    source_id: str
    source_url: str | None
    subreddit: str
    confidence: float


class RelationshipType(str, Enum):
    founder = "founder"
    ceo = "ceo"
    employee = "employee"
    investor = "investor"
    competitor = "competitor"
    parentCompany = "parentCompany"
    subsidiary = "subsidiary"
    partner = "partner"
    acquiredBy = "acquiredBy"
    boardMember = "boardMember"
    advisor = "advisor"
    alumniOf = "alumniOf"
    affiliation = "affiliation"
    critic = "critic"


class RelationshipOut(BaseModel):
    id: int
    type: RelationshipType
    subject: str
    object: str
    confidence: float
    evidence: str | None = None
    source_id: str | None = None
    source_url: str | None = None


class EntityRelationshipSummary(BaseModel):
    type: RelationshipType
    target: str
    count: int


class EntityDetailOut(BaseModel):
    id: int
    canonical_name: str
    aliases: list[str]
    entity_type: str | None
    mentions: list[MentionOut]
    relationships: list[EntityRelationshipSummary]
