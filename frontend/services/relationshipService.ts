import { get } from "./apiClient";
import type { Relationship } from "@/types";

export async function getRelationships(): Promise<Relationship[]> {
  return get<Relationship[]>("/api/relationships");
}
