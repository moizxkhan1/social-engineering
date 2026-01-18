export interface Entity {
  id: number;
  canonical_name: string;
  aliases: string[];
  entity_type: string | null;
  mention_count: number;
}

export interface Mention {
  id: number;
  surface_form: string;
  snippet: string | null;
  source_id: string;
  source_url: string | null;
  subreddit: string;
  confidence: number;
}

export interface EntityRelationshipSummary {
  type: string;
  target: string;
  count: number;
}

export interface EntityDetail {
  id: number;
  canonical_name: string;
  aliases: string[];
  entity_type: string | null;
  mentions: Mention[];
  relationships: EntityRelationshipSummary[];
}
