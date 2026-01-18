"use client";

import { Card, Tag } from "@/components";
import type { CompetitiveOverview } from "@/types";
import { formatPercent } from "@/lib/format";

interface CompetitiveDashboardProps {
  data: CompetitiveOverview | null;
  isLoading?: boolean;
}

export function CompetitiveDashboard({ data, isLoading }: CompetitiveDashboardProps) {
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

  if (!data || data.targets.length === 0) {
    return (
      <Card className="text-center py-8">
        <p className="text-slate-500 dark:text-slate-400">
          No competitive data available yet
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card padding="none">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Share of Voice by Subreddit
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                  Subreddit
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                  Mentions
                </th>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                  Share
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {data.subreddit_share.slice(0, 10).map((row) => (
                <tr key={row.subreddit} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">
                    r/{row.subreddit}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-slate-700 dark:text-slate-300">
                    {row.total}
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex flex-wrap gap-2">
                      {data.targets.map((target) => (
                        <Tag key={`${row.subreddit}-${target}`} variant="default" size="sm">
                          {target}: {formatPercent(row.share[target] || 0)}
                        </Tag>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card padding="none">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Sentiment Distribution
          </h3>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-800/50">
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                  Target
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                  Positive
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                  Neutral
                </th>
                <th className="px-4 py-3 text-right text-xs font-semibold text-slate-600 dark:text-slate-400 uppercase tracking-wider">
                  Negative
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200 dark:divide-slate-700">
              {data.sentiment.map((row) => (
                <tr key={row.target} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="px-4 py-3 text-sm text-slate-700 dark:text-slate-300">
                    {row.target}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-emerald-600 dark:text-emerald-400">
                    {row.positive}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-slate-600 dark:text-slate-400">
                    {row.neutral}
                  </td>
                  <td className="px-4 py-3 text-right text-sm text-red-600 dark:text-red-400">
                    {row.negative}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>

      <Card padding="none">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Co-mentions
          </h3>
        </div>
        <div className="p-4 space-y-2">
          {data.co_mentions.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">No co-mentions yet</p>
          )}
          {data.co_mentions.slice(0, 10).map((item) => (
            <div key={`${item.pair[0]}-${item.pair[1]}`} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Tag variant="info" size="sm">
                  {item.pair[0]}
                </Tag>
                <span className="text-slate-400">&amp;</span>
                <Tag variant="info" size="sm">
                  {item.pair[1]}
                </Tag>
              </div>
              <span className="text-sm text-slate-700 dark:text-slate-300">{item.count}</span>
            </div>
          ))}
        </div>
      </Card>

      <Card padding="none">
        <div className="px-4 py-3 border-b border-slate-200 dark:border-slate-700">
          <h3 className="text-sm font-semibold text-slate-700 dark:text-slate-300">
            Anomalies
          </h3>
        </div>
        <div className="p-4 space-y-2">
          {data.anomalies.length === 0 && (
            <p className="text-sm text-slate-500 dark:text-slate-400">No anomalies detected</p>
          )}
          {data.anomalies.slice(0, 10).map((item, index) => (
            <div key={`${item.target}-${item.date}-${index}`} className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <Tag variant="warning" size="sm">
                  {item.target}
                </Tag>
                <span className="text-sm text-slate-600 dark:text-slate-400">{item.date}</span>
              </div>
              <span className="text-sm text-slate-700 dark:text-slate-300">
                {item.count} (z={item.z_score})
              </span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}
