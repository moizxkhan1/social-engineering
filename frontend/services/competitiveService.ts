import { get } from "./apiClient";
import type { CompetitiveOverview } from "@/types";

export async function getCompetitiveOverview(): Promise<CompetitiveOverview> {
  return get<CompetitiveOverview>("/api/competitive");
}
