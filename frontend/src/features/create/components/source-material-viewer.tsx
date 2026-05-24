"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Alert, AlertDescription, Badge, Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import type { ContentSource } from "@/features/blog/types-ai";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface SourceMaterialViewerProps {
  projectId: string;
}

export function SourceMaterialViewer({ projectId }: SourceMaterialViewerProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  const [sources, setSources] = useState<ContentSource[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadSources = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(API_ENDPOINTS.PROJECT_SOURCES(projectId));
      if (!response.ok) {
        throw new Error("Failed to load sources");
      }
      const payload = (await response.json()) as { items: ContentSource[] };
      setSources(payload.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sources");
    } finally {
      setLoading(false);
    }
  };

  const extractKeyPoints = async (sourceId: string): Promise<void> => {
    const response = await authenticatedFetch(
      API_ENDPOINTS.PROJECT_SOURCE_EXTRACT(projectId, sourceId),
      { method: HTTP_METHODS.POST },
    );
    if (!response.ok) {
      throw new Error("Extraction failed");
    }
    const updated = (await response.json()) as ContentSource;
    setSources((prev) => prev.map((source) => (source.id === sourceId ? updated : source)));
  };

  useEffect(() => {
    void loadSources();
  }, [projectId]);

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <CardTitle>{t("sourcesTitle")}</CardTitle>
        <Button size="sm" variant="outline" disabled={loading} onClick={() => void loadSources()}>
          {t("actions.refresh")}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {sources.length === 0 && <p className="text-sm text-muted-foreground">{t("noSources")}</p>}
        {sources.map((source) => (
          <div key={source.id} className="rounded-md border p-3 space-y-2">
            <div className="flex items-center justify-between">
              <p className="font-medium">{source.title}</p>
              <Badge variant="outline">{source.source_type}</Badge>
            </div>
            <p className="text-sm text-muted-foreground line-clamp-3">{source.content}</p>
            {source.extracted_key_points.length > 0 && (
              <ul className="text-sm list-disc pl-5">
                {source.extracted_key_points.map((point) => (
                  <li key={point}>{point}</li>
                ))}
              </ul>
            )}
            <Button size="sm" onClick={() => void extractKeyPoints(source.id)}>
              {t("actions.extract")}
            </Button>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}
