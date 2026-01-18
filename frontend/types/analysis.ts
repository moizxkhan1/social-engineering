export type JobStatus = "queued" | "running" | "complete" | "failed";

export type ProgressStep =
  | "resolving_company"
  | "discovering_subreddits"
  | "fetching_sources"
  | "llm_extraction"
  | "persisting";

export interface AnalyzeRequest {
  domain: string;
}

export interface AnalyzeResponse {
  job_id: string;
  status: JobStatus;
}

export interface JobResult {
  company_name: string;
  company_aliases?: string[];
  subreddit_count: number;
  source_count: number;
  entity_count: number;
  relationship_count: number;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  progress: ProgressStep | null;
  error: string | null;
  result: JobResult | null;
}
