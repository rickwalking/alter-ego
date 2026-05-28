"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { Badge, Button, Card, CardContent, CardHeader, CardTitle } from "@/components/ui";
import { API_ENDPOINTS } from "@/constants/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

export interface BlogPostVersion {
  version_number: number;
  title: string;
  excerpt?: string;
  snapshot?: Record<string, unknown>;
  created_at?: string;
}

interface VersionHistorySidebarProps {
  postId: string;
  currentBody: string;
  onRestore: (version: BlogPostVersion) => void;
}

export function VersionHistorySidebar({
  postId,
  currentBody,
  onRestore,
}: VersionHistorySidebarProps): React.JSX.Element {
  const t = useTranslations("dashboard.blogPosts.versions");
  const [versions, setVersions] = useState<BlogPostVersion[]>([]);
  const [selected, setSelected] = useState<BlogPostVersion | null>(null);
  const [loading, setLoading] = useState(false);

  const loadVersions = useCallback(async () => {
    setLoading(true);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.BLOG_POST_VERSIONS(postId),
      );
      if (!response.ok) {
        return;
      }
      const data = (await response.json()) as BlogPostVersion[];
      setVersions(data);
    } finally {
      setLoading(false);
    }
  }, [postId]);

  useEffect(() => {
    void loadVersions();
  }, [loadVersions]);

  const selectedBody =
    typeof selected?.snapshot?.body === "string"
      ? selected.snapshot.body
      : "";

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-base">{t("title")}</CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {loading && <p className="text-muted-foreground text-sm">{t("loading")}</p>}
        {!loading && versions.length === 0 && (
          <p className="text-muted-foreground text-sm">{t("empty")}</p>
        )}
        <ul className="max-h-48 space-y-2 overflow-auto">
          {versions.map((version) => (
            <li key={version.version_number}>
              <button
                type="button"
                className="flex w-full items-center justify-between rounded border px-2 py-1 text-left text-sm hover:bg-muted/50"
                onClick={() => setSelected(version)}
              >
                <span>
                  {t("versionLabel", { number: version.version_number })}
                </span>
                <Badge variant="outline">{version.title}</Badge>
              </button>
            </li>
          ))}
        </ul>
        {selected && (
          <div className="space-y-2 rounded border p-2 text-xs">
            <p className="font-medium">{t("diffTitle")}</p>
            <p className="text-muted-foreground whitespace-pre-wrap">
              {selectedBody.slice(0, 400)}
              {selectedBody.length > 400 ? "…" : ""}
            </p>
            <p className="text-muted-foreground whitespace-pre-wrap">
              {currentBody.slice(0, 400)}
              {currentBody.length > 400 ? "…" : ""}
            </p>
            <Button size="sm" variant="outline" onClick={() => onRestore(selected)}>
              {t("restore")}
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
