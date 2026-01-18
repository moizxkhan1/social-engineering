"use client";

import { Card } from "@/components";
import type { JobResult } from "@/types";
import { formatNumber } from "@/lib/format";

interface SummaryCardsProps {
  result: JobResult | null;
}

interface StatCardProps {
  label: string;
  value: string | number;
  icon: React.ReactNode;
  gradientFrom: string;
  gradientTo: string;
}

function StatCard({ label, value, icon, gradientFrom, gradientTo }: StatCardProps) {
  return (
    <Card className="relative overflow-hidden bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700">
      <div className={`absolute top-0 right-0 w-20 h-20 -mr-6 -mt-6 rounded-full bg-gradient-to-br ${gradientFrom} ${gradientTo} opacity-20`} />
      <div className="relative flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
          <p className="mt-2 text-3xl font-bold text-slate-900 dark:text-white">
            {typeof value === "number" ? formatNumber(value) : value}
          </p>
        </div>
        <div className={`p-2.5 rounded-xl bg-gradient-to-br ${gradientFrom} ${gradientTo} shadow-lg`}>
          {icon}
        </div>
      </div>
    </Card>
  );
}

export function SummaryCards({ result }: SummaryCardsProps) {
  if (!result) return null;

  // Backwards-compatible normalization: older backend builds returned different keys.
  const legacy = result as unknown as {
    company?: { name?: string; aliases?: string[] };
    subreddits_discovered?: number;
    subreddits_analyzed?: number;
    entities_found?: number;
    relationships_found?: number;
  };

  const companyName = result.company_name || legacy.company?.name || "—";
  const companyAliases = result.company_aliases || legacy.company?.aliases || [];

  const subredditCount =
    Number.isFinite(result.subreddit_count) ? result.subreddit_count : legacy.subreddits_discovered ?? 0;
  const sourceCount = Number.isFinite(result.source_count) ? result.source_count : 0;
  const entityCount =
    Number.isFinite(result.entity_count) ? result.entity_count : legacy.entities_found ?? 0;
  const relationshipCount =
    Number.isFinite(result.relationship_count) ? result.relationship_count : legacy.relationships_found ?? 0;

  return (
    <div className="space-y-6">
      {/* Company Header */}
      <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
        <div className="flex items-center gap-3">
          <div className="p-2 rounded-lg bg-gradient-to-br from-emerald-500 to-teal-600 shadow-lg shadow-emerald-500/25">
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <div>
            <h3 className="text-lg font-semibold text-slate-900 dark:text-white">
              Analysis Complete
            </h3>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              Results for{" "}
              <span className="font-semibold text-blue-600 dark:text-blue-400">
                {companyName}
              </span>
              {companyAliases.length > 1 && (
                <span className="text-slate-400 dark:text-slate-500">
                  {" "}(also known as: {companyAliases.slice(1, 3).join(", ")})
                </span>
              )}
            </p>
          </div>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Subreddits"
          value={subredditCount}
          gradientFrom="from-purple-500"
          gradientTo="to-indigo-600"
          icon={
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
            </svg>
          }
        />
        <StatCard
          label="Sources"
          value={sourceCount}
          gradientFrom="from-blue-500"
          gradientTo="to-cyan-600"
          icon={
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
          }
        />
        <StatCard
          label="Entities"
          value={entityCount}
          gradientFrom="from-emerald-500"
          gradientTo="to-teal-600"
          icon={
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
            </svg>
          }
        />
        <StatCard
          label="Relationships"
          value={relationshipCount}
          gradientFrom="from-amber-500"
          gradientTo="to-orange-600"
          icon={
            <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
            </svg>
          }
        />
      </div>
    </div>
  );
}
