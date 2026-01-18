import { get } from "./apiClient";
import type { GraphData } from "@/types";

export async function getGraph(): Promise<GraphData> {
  return get<GraphData>("/api/graph");
}
