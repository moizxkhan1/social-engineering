export interface SubredditShare {
  subreddit: string;
  total: number;
  counts: Record<string, number>;
  share: Record<string, number>;
}

export interface SentimentSummary {
  target: string;
  positive: number;
  neutral: number;
  negative: number;
}

export interface CoMentionsSummary {
  pair: [string, string];
  count: number;
}

export interface AnomalySummary {
  target: string;
  date: string;
  count: number;
  z_score: number;
}

export interface CompetitiveOverview {
  targets: string[];
  subreddit_share: SubredditShare[];
  sentiment: SentimentSummary[];
  co_mentions: CoMentionsSummary[];
  anomalies: AnomalySummary[];
}
