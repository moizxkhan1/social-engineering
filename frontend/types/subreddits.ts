export interface Subreddit {
  name: string;
  score: number;
  mention_count: number;
  avg_engagement: number;
  subscribers: number;
  active_user_count: number;
  topic_relevance: number;
  public_description: string | null;
}
