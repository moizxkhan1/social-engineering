"use client";

import { useState, useCallback } from "react";
import { getEntityDetail, ApiError } from "@/services";
import type { EntityDetail } from "@/types";

interface UseEntityDetailReturn {
  entity: EntityDetail | null;
  isLoading: boolean;
  error: string | null;
  fetch: (entityId: number) => Promise<void>;
  clear: () => void;
}

export function useEntityDetail(): UseEntityDetailReturn {
  const [entity, setEntity] = useState<EntityDetail | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(async (entityId: number) => {
    setIsLoading(true);
    setError(null);

    try {
      const detail = await getEntityDetail(entityId);
      setEntity(detail);
    } catch (err) {
      const message =
        err instanceof ApiError ? err.message : "Failed to fetch entity details";
      setError(message);
      setEntity(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const clear = useCallback(() => {
    setEntity(null);
    setError(null);
    setIsLoading(false);
  }, []);

  return {
    entity,
    isLoading,
    error,
    fetch,
    clear,
  };
}
