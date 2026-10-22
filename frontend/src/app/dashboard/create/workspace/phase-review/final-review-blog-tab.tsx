"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { API_ENDPOINTS, DEFAULT_BLOG_LANGUAGE } from "@/constants/api";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { OpenBlogEditorButton } from "@/modules/publishing";

interface PreviewBlogResponse {
  markdown?: string;
}

interface BlogPreview {
  previewMarkdown: string | null;
  previewLoading: boolean;
  previewError: string | null;
}

/** Load the rendered blog preview each time the blog tab is opened (mounted). */
function useBlogPreview(projectId: string, errorMessage: string): BlogPreview {
  const [previewMarkdown, setPreviewMarkdown] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);

  const loadBlogPreview = useCallback(async () => {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.CAROUSEL_PREVIEW_BLOG(projectId, DEFAULT_BLOG_LANGUAGE),
      );
      if (!response.ok) {
        setPreviewError(errorMessage);
        return;
      }
      const payload = (await response.json()) as PreviewBlogResponse;
      setPreviewMarkdown(payload.markdown ?? "");
    } catch {
      setPreviewError(errorMessage);
    } finally {
      setPreviewLoading(false);
    }
  }, [projectId, errorMessage]);

  useEffect(() => {
    void loadBlogPreview();
  }, [loadBlogPreview]);

  return { previewMarkdown, previewLoading, previewError };
}

interface BlogPreviewPanelProps {
  readonly loading: boolean;
  readonly error: string | null;
  readonly markdown: string;
  readonly loadingText: string;
  readonly placeholderText: string;
}

function blogPreviewContent({
  loading,
  error,
  markdown,
  loadingText,
  placeholderText,
}: BlogPreviewPanelProps): React.JSX.Element {
  const muted = "text-[var(--color-text-muted)]";
  if (loading) {
    return <p className={muted}>{loadingText}</p>;
  }
  if (error) {
    return <p className={muted}>{error}</p>;
  }
  if (!markdown) {
    return <p className={muted}>{placeholderText}</p>;
  }
  return (
    <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-[var(--color-surface)] p-3 text-[var(--color-text-muted)] text-xs">
      {markdown}
    </pre>
  );
}

/** Loading, error, the rendered markdown, or the empty placeholder. */
function BlogPreviewPanel(props: BlogPreviewPanelProps): React.JSX.Element {
  return <div className="space-y-2">{blogPreviewContent(props)}</div>;
}

interface FinalReviewBlogTabProps {
  readonly projectId: string;
  /** The checkpoint's blog markdown, shown until the preview loads. */
  readonly fallbackMarkdown: string;
}

/**
 * The blog draft preview of the final review and the way to the blog editor,
 * where the blog body is edited (it is not edited inline here).
 */
export function FinalReviewBlogTab({
  projectId,
  fallbackMarkdown,
}: FinalReviewBlogTabProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.review.finalReview");
  const { previewMarkdown, previewLoading, previewError } = useBlogPreview(
    projectId,
    t("blogPreviewError"),
  );
  return (
    <div className="space-y-3">
      <BlogPreviewPanel
        loading={previewLoading}
        error={previewError}
        markdown={previewMarkdown ?? fallbackMarkdown}
        loadingText={t("blogPreviewLoading")}
        placeholderText={t("blogPlaceholder")}
      />
      <OpenBlogEditorButton projectId={projectId} />
    </div>
  );
}
