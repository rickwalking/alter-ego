"use client";

import { useCallback, useEffect, useState } from "react";
import { CONTENT_SOURCE_TYPES } from "@/constants/blog-ai";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import type { ContentSource } from "@/modules/publishing";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

const ERR_LOAD_SOURCES = "Failed to load sources";
const ERR_ADD_SOURCE = "Failed to add source";
const ERR_EXTRACT = "Extraction failed";

function errorMessage(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback;
}

export interface ProjectSources {
  sources: ContentSource[];
  loading: boolean;
  error: string | null;
  setError: (error: string | null) => void;
  loadSources: () => Promise<void>;
  updateSources: (next: ContentSource[]) => void;
  extractKeyPoints: (sourceId: string) => Promise<void>;
}

/** The project's source list: load on mount, refresh, extract key points. */
export function useProjectSources(
  projectId: string,
  onSourcesChange?: (sources: ContentSource[]) => void,
): ProjectSources {
  const [sources, setSources] = useState<ContentSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const updateSources = useCallback(
    (next: ContentSource[]) => {
      setSources(next);
      onSourcesChange?.(next);
    },
    [onSourcesChange],
  );

  const loadSources = useCallback(async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      updateSources(await fetchSources(projectId));
    } catch (err) {
      setError(errorMessage(err, ERR_LOAD_SOURCES));
    } finally {
      setLoading(false);
    }
  }, [projectId, updateSources]);

  const extractKeyPoints = async (sourceId: string): Promise<void> => {
    const updated = await postExtract(projectId, sourceId);
    updateSources(
      sources.map((source) => (source.id === sourceId ? updated : source)),
    );
  };

  useEffect(() => {
    void loadSources();
  }, [loadSources]);

  return {
    sources,
    loading,
    error,
    setError,
    loadSources,
    updateSources,
    extractKeyPoints,
  };
}

export interface SourceForm {
  title: string;
  setTitle: (value: string) => void;
  content: string;
  setContent: (value: string) => void;
  sourceType: string;
  setSourceType: (value: string) => void;
  adding: boolean;
  addSource: (event: React.SubmitEvent<HTMLFormElement>) => Promise<void>;
}

/** The "add a source" form: POST, prepend the result, then reset. */
export function useSourceForm(
  projectId: string,
  list: ProjectSources,
): SourceForm {
  const [adding, setAdding] = useState(false);
  const [title, setTitle] = useState("");
  const [content, setContent] = useState("");
  const [sourceType, setSourceType] = useState<string>(
    CONTENT_SOURCE_TYPES.NOTE,
  );

  const addSource = async (
    event: React.SubmitEvent<HTMLFormElement>,
  ): Promise<void> => {
    event.preventDefault();
    if (!title.trim() || !content.trim()) {
      return;
    }
    setAdding(true);
    list.setError(null);
    try {
      const created = await postSource(projectId, {
        title: title.trim(),
        content: content.trim(),
        source_type: sourceType,
      });
      list.updateSources([created, ...list.sources]);
      setTitle("");
      setContent("");
      setSourceType(CONTENT_SOURCE_TYPES.NOTE);
    } catch (err) {
      list.setError(errorMessage(err, ERR_ADD_SOURCE));
    } finally {
      setAdding(false);
    }
  };

  return {
    title,
    setTitle,
    content,
    setContent,
    sourceType,
    setSourceType,
    adding,
    addSource,
  };
}

async function postSource(
  projectId: string,
  body: { title: string; content: string; source_type: string },
): Promise<ContentSource> {
  const response = await authenticatedFetch(
    API_ENDPOINTS.PROJECT_SOURCES(projectId),
    { method: HTTP_METHODS.POST, body: JSON.stringify(body) },
  );
  if (!response.ok) {
    throw new Error(ERR_ADD_SOURCE);
  }
  return (await response.json()) as ContentSource;
}

async function fetchSources(projectId: string): Promise<ContentSource[]> {
  const response = await authenticatedFetch(
    API_ENDPOINTS.PROJECT_SOURCES(projectId),
  );
  if (!response.ok) {
    throw new Error(ERR_LOAD_SOURCES);
  }
  const payload = (await response.json()) as { items: ContentSource[] };
  return payload.items;
}

async function postExtract(
  projectId: string,
  sourceId: string,
): Promise<ContentSource> {
  const response = await authenticatedFetch(
    API_ENDPOINTS.PROJECT_SOURCE_EXTRACT(projectId, sourceId),
    { method: HTTP_METHODS.POST },
  );
  if (!response.ok) {
    throw new Error(ERR_EXTRACT);
  }
  return (await response.json()) as ContentSource;
}
