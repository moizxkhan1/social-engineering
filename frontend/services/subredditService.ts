import { get } from "./apiClient";
import type { Subreddit } from "@/types";

export async function getSubreddits(): Promise<Subreddit[]> {
  return get<Subreddit[]>("/api/subreddits");
}
