"use client";

import { Card, Tag } from "@/components";
import type { Relationship } from "@/types";
import { formatRelationshipType, formatConfidence, truncate } from "@/lib/format";

interface RelationshipListProps {
  relationships: Relationship[];
  isLoading?: boolean;
}

function getRelationshipVariant(type: string): "primary" | "success" | "warning" | "info" | "default" {
  switch (type) {
    case "founder":
    case "ceo":
    case "boardMember":
      return "primary";
    case "investor":
    case "acquiredBy":
      return "success";
    case "competitor":
    case "critic":
      return "warning";
    case "employee":
    case "partner":
      return "info";
    default:
      return "default";
  }
}

export function RelationshipList({ relationships, isLoading }: RelationshipListProps) {
  if (isLoading) {
    return (
      <Card>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-16 bg-slate-200 dark:bg-slate-700 rounded" />
          ))}
        </div>
      </Card>
    );
  }

  if (relationships.length === 0) {
    return (
      <Card className="text-center py-8">
        <p className="text-slate-500 dark:text-slate-400">No relationships extracted yet</p>
      </Card>
    );
  }

  return (
    <Card padding="none">
      <div className="divide-y divide-slate-200 dark:divide-slate-700">
        {relationships.map((rel) => (
          <div
            key={rel.id}
            className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors"
          >
            <div className="flex items-center gap-3 mb-2">
              <span className="font-medium text-slate-900 dark:text-white">
                {rel.subject}
              </span>
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
              <Tag variant={getRelationshipVariant(rel.type)} size="sm">
                {formatRelationshipType(rel.type)}
              </Tag>
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 8l4 4m0 0l-4 4m4-4H3" />
              </svg>
              <span className="font-medium text-slate-900 dark:text-white">
                {rel.object}
              </span>
              <Tag variant="default" size="sm">
                {formatConfidence(rel.confidence)}
              </Tag>
            </div>
            {rel.evidence && (
              <p className="text-sm text-slate-500 dark:text-slate-400 italic pl-4 border-l-2 border-slate-200 dark:border-slate-700">
                &ldquo;{truncate(rel.evidence, 150)}&rdquo;
              </p>
            )}
            {rel.source_url && (
              <div className="mt-2">
                <a
                  href={rel.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-sm text-blue-600 dark:text-blue-400 hover:underline inline-flex items-center gap-1"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                  View source
                </a>
              </div>
            )}
          </div>
        ))}
      </div>
    </Card>
  );
}
