from __future__ import annotations

import json
from dataclasses import dataclass

from openai import OpenAI
from pydantic import BaseModel, Field, ValidationError


class LLMConfigError(RuntimeError):
    pass


class CompanyResolution(BaseModel):
    name: str
    aliases: list[str] = Field(default_factory=list)


class ExtractedEntity(BaseModel):
    canonical_name: str
    aliases: list[str] = Field(default_factory=list)
    entity_type: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class ExtractedRelationship(BaseModel):
    subject: str
    relationship: str
    object: str
    confidence: float = Field(ge=0.0, le=1.0)
    evidence: str | None = None


class ExtractionResult(BaseModel):
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


class SourceExtraction(BaseModel):
    source_id: str
    entities: list[ExtractedEntity] = Field(default_factory=list)
    relationships: list[ExtractedRelationship] = Field(default_factory=list)


class BatchExtractionResult(BaseModel):
    results: list[SourceExtraction] = Field(default_factory=list)


@dataclass
class LLMClient:
    api_key: str
    model: str

    def __post_init__(self) -> None:
        if not self.api_key:
            raise LLMConfigError("OPENAI_API_KEY is required for LLM extraction")
        self._client = OpenAI(api_key=self.api_key)

    def resolve_company(self, domain: str, hint_name: str) -> CompanyResolution:
        system = (
            "You resolve company names from domains. "
            "Return compact JSON only."
        )
        user = (
            "Resolve the company name and aliases.\n"
            f"Domain: {domain}\n"
            f"Hint: {hint_name}\n\n"
            "Return JSON with keys: name (string), aliases (array of strings). "
            "Include the canonical name in aliases."
        )
        payload = self._call_json(system, user)
        return CompanyResolution.model_validate(payload)

    def extract_entities_relationships(
        self,
        *,
        text: str,
        company_name: str,
        aliases: list[str],
        relationship_types: list[str],
    ) -> ExtractionResult:
        system = (
            "Extract entities and relationships from text. "
            "Use only the provided relationship types. "
            "Return JSON only."
        )
        alias_str = ", ".join(aliases) if aliases else "none"
        rel_str = ", ".join(relationship_types)
        user = (
            f"Company context: {company_name} (aliases: {alias_str})\n\n"
            f"Text:\n{text}\n\n"
            "Return JSON with keys: entities, relationships.\n"
            "entities: array of {canonical_name, aliases, entity_type, confidence}.\n"
            "relationships: array of {subject, relationship, object, confidence, evidence}.\n"
            f"relationship must be one of: {rel_str}.\n"
            "confidence is 0-1.\n"
            "Return JSON only."
        )
        payload = self._call_json(system, user)
        return ExtractionResult.model_validate(payload)

    def extract_entities_relationships_batch(
        self,
        *,
        sources: list[dict],
        company_name: str,
        aliases: list[str],
        relationship_types: list[str],
    ) -> BatchExtractionResult:
        system = (
            "Extract entities and relationships from each source. "
            "Use only the provided relationship types. "
            "Return JSON only."
        )
        alias_str = ", ".join(aliases) if aliases else "none"
        rel_str = ", ".join(relationship_types)
        blocks = []
        for source in sources:
            source_id = source.get("id")
            text = source.get("text", "")
            blocks.append(f"Source {source_id}:\n{text}")
        sources_blob = "\n\n".join(blocks)

        user = (
            f"Company context: {company_name} (aliases: {alias_str})\n\n"
            f"Sources:\n{sources_blob}\n\n"
            "Return JSON with key: results.\n"
            "results: array of {source_id, entities, relationships}.\n"
            "entities: array of {canonical_name, aliases, entity_type, confidence}.\n"
            "relationships: array of {subject, relationship, object, confidence, evidence}.\n"
            f"relationship must be one of: {rel_str}.\n"
            "confidence is 0-1.\n"
            "Return JSON only."
        )
        payload = self._call_json(system, user)
        return BatchExtractionResult.model_validate(payload)

    def _call_json(self, system_prompt: str, user_prompt: str) -> dict:
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content or ""
        return _parse_json(content)


def _parse_json(content: str) -> dict:
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("LLM response did not contain JSON object")
    data = json.loads(content[start : end + 1])
    if not isinstance(data, dict):
        raise ValueError("LLM JSON response was not an object")
    return data
