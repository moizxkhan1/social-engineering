"use client";

import { Card, Tag } from "@/components";
import type { Subreddit } from "@/types";
import { formatNumber } from "@/lib/format";

interface SubredditTableProps {
  subreddits: Subreddit[];
  isLoading?: boolean;
}

export function SubredditTable({ subreddits, isLoading }: SubredditTableProps) {
  if (isLoading) {
    return (
      <Card>
        <div className="animate-pulse space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-12 bg-slate-200 dark:bg-slate-700 rounded" />
          ))}
        </div>
      </Card>
    );
  }

  if (subreddits.length === 0) {
    return (
      <Card className="text-center py-8">
        <p className="text-slate-500 dark:text-slate-400">No subreddits discovered yet</p>
      </Card>
    );
  }

  return (
    <Card padding="none">
      <div className="overflow-x-auto">
        <table className="w-full">
          <thead>
            <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
              <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Subreddit
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Score
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Mentions
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Subscribers
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Engagement
              </th>
              <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                Relevance
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
            {subreddits.map((sub, index) => (
              <tr
                key={sub.name}
                className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
              >
                <td className="px-4 py-3">
                  <div className="flex items-center gap-3">
                    <span className="text-sm text-slate-400 dark:text-slate-500 w-5">
                      {index + 1}
                    </span>
                    <div>
                      <a
                        href={`https://reddit.com/r/${sub.name}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="font-medium text-blue-600 dark:text-blue-400 hover:underline"
                      >
                        r/{sub.name}
                      </a>
                      {sub.public_description && (
                        <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5 line-clamp-1 max-w-xs">
                          {sub.public_description}
                        </p>
                      )}
                    </div>
                  </div>
                </td>
                <td className="px-4 py-3 text-right">
                  <Tag variant="primary" size="sm">
                    {sub.score.toFixed(2)}
                  </Tag>
                </td>
                <td className="px-4 py-3 text-right text-sm text-slate-700 dark:text-slate-300">
                  {sub.mention_count}
                </td>
                <td className="px-4 py-3 text-right text-sm text-slate-700 dark:text-slate-300">
                  {formatNumber(sub.subscribers)}
                </td>
                <td className="px-4 py-3 text-right text-sm text-slate-700 dark:text-slate-300">
                  {sub.avg_engagement.toFixed(1)}
                </td>
                <td className="px-4 py-3 text-right">
                  <RelevanceIndicator value={sub.topic_relevance} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

function RelevanceIndicator({ value }: { value: number }) {
  const bars = 5;
  const filled = Math.round((value / 10) * bars);

  return (
    <div className="flex items-center justify-end gap-0.5">
      {Array.from({ length: bars }).map((_, i) => (
        <div
          key={i}
          className={`w-1.5 h-4 rounded-sm ${
            i < filled
              ? "bg-emerald-500"
              : "bg-slate-200 dark:bg-slate-600"
          }`}
        />
      ))}
    </div>
  );
}
