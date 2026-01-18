export type RelationshipType =
  | "founder"
  | "ceo"
  | "employee"
  | "investor"
  | "competitor"
  | "parentCompany"
  | "subsidiary"
  | "partner"
  | "acquiredBy"
  | "boardMember"
  | "advisor"
  | "alumniOf"
  | "affiliation"
  | "critic";

export interface Relationship {
  id: number;
  type: RelationshipType;
  subject: string;
  object: string;
  confidence: number;
  evidence: string | null;
  source_id: string | null;
  source_url: string | null;
}
