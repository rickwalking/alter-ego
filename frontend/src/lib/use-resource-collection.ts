/**
 * One list + create/update/delete hook for a REST collection
 * (personas and rubrics carried two copies of it). Error messages keep the
 * per-resource wording ("Failed to create persona").
 */
import { useCallback, useEffect, useState } from "react";
import type { Dispatch, SetStateAction } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { API_BASE } from "@/constants/api";

const FALLBACK_ERROR = "An error occurred";

export interface ResourceCollectionConfig {
  /** Collection path under the API base, e.g. "personas". */
  path: string;
  /** Singular noun used in error messages, e.g. "persona". */
  noun: string;
}

export interface ResourceCollection<T, C, U> {
  items: T[];
  loading: boolean;
  error: string | null;
  refetch: () => Promise<void>;
  create: (data: C) => Promise<T>;
  update: (id: string, data: U) => Promise<T>;
  delete: (id: string) => Promise<boolean>;
}

async function sendJson<T>(
  url: string,
  init: RequestInit,
  failure: string,
): Promise<T> {
  const response = await authenticatedFetch(url, init);
  if (!response.ok) {
    throw new Error(failure);
  }
  return (await response.json()) as T;
}

async function removeItem(url: string, failure: string): Promise<void> {
  const response = await authenticatedFetch(url, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(failure);
  }
}

async function fetchItems<T>(path: string): Promise<T[]> {
  const data = await sendJson<{ items: T[] }>(
    `${API_BASE}/${path}`,
    {},
    `Failed to fetch ${path}`,
  );
  return data.items;
}

type SetItems<T> = Dispatch<SetStateAction<T[]>>;

function mutations<T extends { id: string }, C, U>(
  { path, noun }: ResourceCollectionConfig,
  setItems: SetItems<T>,
): Pick<ResourceCollection<T, C, U>, "create" | "update" | "delete"> {
  const url = (id?: string): string =>
    id ? `${API_BASE}/${path}/${id}` : `${API_BASE}/${path}`;
  return {
    create: async (data) => {
      const init = { method: "POST", body: JSON.stringify(data) };
      const item = await sendJson<T>(url(), init, `Failed to create ${noun}`);
      setItems((prev) => [item, ...prev]);
      return item;
    },
    update: async (id, data) => {
      const init = { method: "PUT", body: JSON.stringify(data) };
      const item = await sendJson<T>(url(id), init, `Failed to update ${noun}`);
      setItems((prev) => prev.map((p) => (p.id === id ? item : p)));
      return item;
    },
    delete: async (id) => {
      await removeItem(url(id), `Failed to delete ${noun}`);
      setItems((prev) => prev.filter((p) => p.id !== id));
      return true;
    },
  };
}

/** Run the (stable) loader once the consumer mounts. */
function useLoadOnMount(load: () => Promise<void>): void {
  useEffect(() => {
    void load();
  }, [load]);
}

export function useResourceCollection<T extends { id: string }, C, U>(
  config: ResourceCollectionConfig,
): ResourceCollection<T, C, U> {
  const [items, setItems] = useState<T[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const { path } = config;
  const refetch = useCallback(async (): Promise<void> => {
    try {
      setLoading(true);
      setItems(await fetchItems<T>(path));
    } catch (err) {
      setError(err instanceof Error ? err.message : FALLBACK_ERROR);
    } finally {
      setLoading(false);
    }
  }, [path]);

  useLoadOnMount(refetch);

  return {
    items,
    loading,
    error,
    refetch,
    ...mutations<T, C, U>(config, setItems),
  };
}
