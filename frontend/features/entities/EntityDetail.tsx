"use client";

import { Card, CardHeader, CardTitle, CardContent, Tag, Button } from "@/components";
import type { EntityDetail as EntityDetailType } from "@/types";
import { formatRelationshipType, formatConfidence, truncate } from "@/lib/format";

interface EntityDetailProps {
  entity: EntityDetailType | null;
  isLoading: boolean;
  error: string | null;
  onClose: () => void;
}

export function EntityDetail({ entity, isLoading, error, onClose }: EntityDetailProps) {
  if (!entity && !isLoading && !error) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50">
      <Card className="w-full max-w-2xl max-h-[80vh] overflow-hidden flex flex-col" padding="none">
        <CardHeader className="flex items-center justify-between flex-shrink-0">
          <div>
            {isLoading ? (
              <div className="h-6 w-48 bg-slate-200 dark:bg-slate-700 rounded animate-pulse" />
            ) : entity ? (
              <div className="flex items-center gap-2">
                <CardTitle>{entity.canonical_name}</CardTitle>
                {entity.entity_type && (
                  <Tag variant="primary" size="sm">
                    {entity.entity_type}
                  </Tag>
                )}
              </div>
            ) : (
              <CardTitle>Entity Details</CardTitle>
            )}
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </Button>
        </CardHeader>

        <div className="flex-1 overflow-y-auto">
          {isLoading && (
            <CardContent>
              <div className="animate-pulse space-y-4">
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded w-1/2" />
                <div className="h-20 bg-slate-200 dark:bg-slate-700 rounded" />
                <div className="h-20 bg-slate-200 dark:bg-slate-700 rounded" />
              </div>
            </CardContent>
          )}

          {error && (
            <CardContent>
              <div className="flex items-center gap-2 text-red-600 dark:text-red-400">
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>{error}</span>
              </div>
            </CardContent>
          )}

          {entity && !isLoading && (
            <CardContent className="space-y-6">
              {/* Aliases */}
              {entity.aliases.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                    Also known as
                  </h4>
                  <div className="flex flex-wrap gap-2">
                    {entity.aliases.map((alias) => (
                      <Tag key={alias} variant="default" size="sm">
                        {alias}
                      </Tag>
                    ))}
                  </div>
                </div>
              )}

              {/* Relationships */}
              {entity.relationships.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                    Relationships
                  </h4>
                  <div className="space-y-2">
                    {entity.relationships.map((rel, i) => (
                      <div
                        key={i}
                        className="flex items-center justify-between p-2 bg-slate-50 dark:bg-slate-800 rounded-lg"
                      >
                        <div className="flex items-center gap-2">
                          <Tag variant="info" size="sm">
                            {formatRelationshipType(rel.type)}
                          </Tag>
                          <span className="text-sm text-slate-700 dark:text-slate-300">
                            {rel.target}
                          </span>
                        </div>
                        <span className="text-sm text-slate-500 dark:text-slate-400">
                          {rel.count} {rel.count === 1 ? "mention" : "mentions"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Mentions */}
              {entity.mentions.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-slate-500 dark:text-slate-400 mb-2">
                    Mentions ({entity.mentions.length})
                  </h4>
                  <div className="space-y-2 max-h-60 overflow-y-auto">
                    {entity.mentions.map((mention) => (
                      <div
                        key={mention.id}
                        className="p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700"
                      >
                        <div className="flex items-center justify-between mb-2">
                          <div className="flex items-center gap-2">
                            <a
                              href={`https://reddit.com/r/${mention.subreddit}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm font-medium text-blue-600 dark:text-blue-400 hover:underline"
                            >
                              r/{mention.subreddit}
                            </a>
                            <Tag variant="default" size="sm">
                              {formatConfidence(mention.confidence)}
                            </Tag>
                          </div>
                          {mention.source_url && (
                            <a
                              href={mention.source_url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-sm text-blue-600 dark:text-blue-400 hover:underline"
                            >
                              View source
                            </a>
                          )}
                        </div>
                        {mention.snippet && (
                          <p className="text-sm text-slate-600 dark:text-slate-400 italic">
                            &ldquo;{truncate(mention.snippet, 200)}&rdquo;
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </CardContent>
          )}
        </div>
      </Card>
    </div>
  );
}
