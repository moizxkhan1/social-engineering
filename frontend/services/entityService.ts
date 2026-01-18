import { get } from "./apiClient";
import type { Entity, EntityDetail } from "@/types";

export async function getEntities(): Promise<Entity[]> {
  return get<Entity[]>("/api/entities");
}

export async function getEntityDetail(entityId: number): Promise<EntityDetail> {
  return get<EntityDetail>(`/api/entities/${entityId}`);
}
