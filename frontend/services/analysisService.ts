import { get, post } from "./apiClient";
import type { AnalyzeRequest, AnalyzeResponse, JobResponse } from "@/types";

export async function startAnalysis(domain: string): Promise<AnalyzeResponse> {
  return post<AnalyzeResponse, AnalyzeRequest>("/api/analyze", { domain });
}

export async function getJobStatus(jobId: string): Promise<JobResponse> {
  return get<JobResponse>(`/api/jobs/${jobId}`);
}
