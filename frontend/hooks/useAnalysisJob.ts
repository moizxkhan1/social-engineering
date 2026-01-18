"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { startAnalysis, getJobStatus, ApiError } from "@/services";
import type { JobResponse, JobStatus, ProgressStep } from "@/types";

const POLL_INTERVAL = 1500;

interface UseAnalysisJobReturn {
  jobId: string | null;
  status: JobStatus | null;
  progress: ProgressStep | null;
  error: string | null;
  result: JobResponse["result"];
  isLoading: boolean;
  start: (domain: string) => Promise<void>;
  reset: () => void;
}

export function useAnalysisJob(): UseAnalysisJobReturn {
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatus | null>(null);
  const [progress, setProgress] = useState<ProgressStep | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<JobResponse["result"]>(null);
  const [isLoading, setIsLoading] = useState(false);

  const pollRef = useRef<NodeJS.Timeout | null>(null);

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  const poll = useCallback(
    async (id: string) => {
      try {
        const job = await getJobStatus(id);
        setStatus(job.status);
        setProgress(job.progress);

        if (job.status === "complete") {
          setResult(job.result);
          setIsLoading(false);
          stopPolling();
        } else if (job.status === "failed") {
          setError(job.error || "Analysis failed");
          setIsLoading(false);
          stopPolling();
        }
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Failed to fetch job status";
        setError(message);
        setIsLoading(false);
        stopPolling();
      }
    },
    [stopPolling]
  );

  const start = useCallback(
    async (domain: string) => {
      stopPolling();
      setError(null);
      setResult(null);
      setProgress(null);
      setIsLoading(true);

      try {
        const response = await startAnalysis(domain);
        setJobId(response.job_id);
        setStatus(response.status);

        // Start polling
        pollRef.current = setInterval(() => {
          poll(response.job_id);
        }, POLL_INTERVAL);

        // Initial poll
        poll(response.job_id);
      } catch (err) {
        const message =
          err instanceof ApiError ? err.message : "Failed to start analysis";
        setError(message);
        setIsLoading(false);
      }
    },
    [poll, stopPolling]
  );

  const reset = useCallback(() => {
    stopPolling();
    setJobId(null);
    setStatus(null);
    setProgress(null);
    setError(null);
    setResult(null);
    setIsLoading(false);
  }, [stopPolling]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      stopPolling();
    };
  }, [stopPolling]);

  return {
    jobId,
    status,
    progress,
    error,
    result,
    isLoading,
    start,
    reset,
  };
}
