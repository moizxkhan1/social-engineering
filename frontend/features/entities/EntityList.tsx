"use client";

import { Card, Tag, Button } from "@/components";
import type { Entity } from "@/types";

interface EntityListProps {
  entities: Entity[];
  isLoading?: boolean;
  onSelect: (entity: Entity) => void;
}

function getEntityTypeVariant(type: string | null): "default" | "primary" | "info" {
  switch (type?.toLowerCase()) {
    case "company":
    case "organization":
      return "primary";
    case "person":
      return "info";
    default:
      return "default";
  }
}

export function EntityList({ entities, isLoading, onSelect }: EntityListProps) {
  if (isLoading) {
    return (
      <Card>
        <div className="animate-pulse space-y-3">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-16 bg-slate-200 dark:bg-slate-700 rounded" />
          ))}
        </div>
      </Card>
    );
  }

  if (entities.length === 0) {
    return (
      <Card className="text-center py-8">
        <p className="text-slate-500 dark:text-slate-400">No entities extracted yet</p>
      </Card>
    );
  }

  return (
    <Card padding="none">
      <div className="divide-y divide-slate-200 dark:divide-slate-700">
        {entities.map((entity) => (
          <div
            key={entity.id}
            className="p-4 hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors cursor-pointer"
            onClick={() => onSelect(entity)}
          >
            <div className="flex items-start justify-between gap-4">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <h4 className="font-medium text-slate-900 dark:text-white">
                    {entity.canonical_name}
                  </h4>
                  {entity.entity_type && (
                    <Tag variant={getEntityTypeVariant(entity.entity_type)} size="sm">
                      {entity.entity_type}
                    </Tag>
                  )}
                </div>
                {entity.aliases.length > 0 && (
                  <p className="mt-1 text-sm text-slate-500 dark:text-slate-400 truncate">
                    Also: {entity.aliases.join(", ")}
                  </p>
                )}
              </div>
              <div className="flex items-center gap-3">
                <div className="text-right">
                  <p className="text-2xl font-bold text-slate-900 dark:text-white">
                    {entity.mention_count}
                  </p>
                  <p className="text-xs text-slate-500 dark:text-slate-400">mentions</p>
                </div>
                <Button variant="ghost" size="sm">
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                  </svg>
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
