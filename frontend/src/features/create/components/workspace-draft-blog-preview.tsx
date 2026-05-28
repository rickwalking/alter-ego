"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { API_ENDPOINTS, DEFAULT_BLOG_LANGUAGE } from "@/constants/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface WorkspaceDraftBlogPreviewProps {
  projectId: string;
}

interface PreviewBlogResponse {
  markdown?: string;
}

export function WorkspaceDraftBlogPreview({
  projectId,
}: WorkspaceDraftBlogPreviewProps): React.JSX.Element {
  const t = useTranslations("create.workspace");
  const [markdown, setMarkdown] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.CAROUSEL_PREVIEW_BLOG(projectId, DEFAULT_BLOG_LANGUAGE),
      );
      if (!response.ok) {
        setError(t("previewError"));
        return;
      }
      const payload = (await response.json()) as PreviewBlogResponse;
      setMarkdown(payload.markdown ?? "");
    } catch {
      setError(t("previewError"));
    } finally {
      setLoading(false);
    }
  }, [projectId, t]);

  return (
    <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] p-4">
      <div className="flex items-center justify-between gap-2">
        <h3 className="font-medium text-sm">{t("draftBlogPreview")}</h3>
        <button
          type="button"
          onClick={() => void loadPreview()}
          disabled={loading}
          className="rounded-md border border-[var(--color-border)] px-3 py-1 font-medium text-xs transition-colors hover:bg-[var(--color-surface)] disabled:opacity-50"
        >
          {loading ? t("loadingPreview") : t("loadDraftBlog")}
        </button>
      </div>
      {error ? (
        <p className="mt-2 text-[var(--color-text-muted)] text-sm">{error}</p>
      ) : null}
      {markdown !== null ? (
        <pre className="mt-3 max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-[var(--color-surface)] p-3 text-[var(--color-text-muted)] text-xs">
          {markdown || t("previewEmpty")}
        </pre>
      ) : null}
    </div>
  );
}
