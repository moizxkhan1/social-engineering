"use client";

import { Card, Tag, Button } from "@/components";
import type { JobStatus as JobStatusType, ProgressStep } from "@/types";

interface JobStatusProps {
  status: JobStatusType | null;
  progress: ProgressStep | null;
  error: string | null;
  onRetry?: () => void;
}

const progressLabels: Record<ProgressStep, string> = {
  resolving_company: "Resolving company name...",
  discovering_subreddits: "Discovering relevant subreddits...",
  fetching_sources: "Fetching posts and comments...",
  llm_extraction: "Extracting entities and relationships...",
  persisting: "Saving results...",
};

const progressPercent: Record<ProgressStep, number> = {
  resolving_company: 10,
  discovering_subreddits: 25,
  fetching_sources: 50,
  llm_extraction: 75,
  persisting: 95,
};

export function JobStatus({ status, progress, error, onRetry }: JobStatusProps) {
  if (!status) return null;

  const isRunning = status === "running" || status === "queued";
  const isComplete = status === "complete";
  const isFailed = status === "failed";

  const percent = progress ? progressPercent[progress] : status === "complete" ? 100 : 0;

  return (
    <Card padding="none" className="overflow-hidden">
      <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-sm font-medium text-slate-700 dark:text-slate-300">
            Analysis Status
          </span>
          {isRunning && (
            <Tag variant="info" size="sm">
              Running
            </Tag>
          )}
          {isComplete && (
            <Tag variant="success" size="sm">
              Complete
            </Tag>
          )}
          {isFailed && (
            <Tag variant="danger" size="sm">
              Failed
            </Tag>
          )}
        </div>
        {isFailed && onRetry && (
          <Button variant="ghost" size="sm" onClick={onRetry}>
            Retry
          </Button>
        )}
      </div>

      <div className="p-4">
        {isRunning && (
          <div className="space-y-3">
            <div className="h-2 bg-slate-200 dark:bg-slate-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-blue-500 to-indigo-500 rounded-full transition-all duration-500 ease-out"
                style={{ width: `${percent}%` }}
              />
            </div>
            <p className="text-sm text-slate-600 dark:text-slate-400">
              {progress ? progressLabels[progress] : "Initializing..."}
            </p>
          </div>
        )}

        {isComplete && (
          <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M5 13l4 4L19 7"
              />
            </svg>
            <span className="text-sm font-medium">Analysis completed successfully</span>
          </div>
        )}

        {isFailed && error && (
          <div className="flex items-start gap-2 text-red-600 dark:text-red-400">
            <svg
              className="w-5 h-5 flex-shrink-0 mt-0.5"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
            <span className="text-sm">{error}</span>
          </div>
        )}
      </div>
    </Card>
  );
}
