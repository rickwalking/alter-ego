"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { API_ENDPOINTS, DEFAULT_BLOG_LANGUAGE } from "@/constants/api";
import { cn } from "@/lib/utils";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  FINAL_REVIEW_TABS,
  type FinalReviewTab,
} from "@/constants/editorial-workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { ContentPhaseReview } from "@/app/dashboard/create/workspace/phase-review/content-phase-review";
import {
  resolveBlogMarkdown,
  resolveCaption,
  resolveRubricScores,
} from "./create-phase-review-helpers";

interface FinalReviewTabsProps {
  projectId: string;
  state: EditorialWorkflowState;
}

interface PreviewBlogResponse {
  markdown?: string;
}

interface BlogPreview {
  previewMarkdown: string | null;
  previewLoading: boolean;
  previewError: string | null;
}

/** Load the rendered blog preview each time the blog tab is opened. */
function useBlogPreview(
  projectId: string,
  active: boolean,
  errorMessage: string,
): BlogPreview {
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
    if (!active) {
      return;
    }
    void loadBlogPreview();
  }, [active, loadBlogPreview]);

  return { previewMarkdown, previewLoading, previewError };
}

interface BlogPreviewPanelProps {
  loading: boolean;
  error: string | null;
  markdown: string;
  loadingText: string;
  placeholderText: string;
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

export function CreateFinalReviewTabs({
  projectId,
  state,
}: FinalReviewTabsProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.review.finalReview");
  const [activeTab, setActiveTab] = useState<FinalReviewTab>(
    FINAL_REVIEW_TABS.CAROUSEL,
  );
  const caption = resolveCaption(state);
  const blogMarkdown = resolveBlogMarkdown(state);
  const rubricScores = resolveRubricScores(state);
  const scoreEntries = Object.entries(rubricScores);
  const { previewMarkdown, previewLoading, previewError } = useBlogPreview(
    projectId,
    activeTab === FINAL_REVIEW_TABS.BLOG,
    t("blogPreviewError"),
  );

  const displayedBlogMarkdown = previewMarkdown ?? blogMarkdown;

  const tabs: Array<{ id: FinalReviewTab; label: string }> = [
    { id: FINAL_REVIEW_TABS.CAROUSEL, label: t("tabs.carousel") },
    { id: FINAL_REVIEW_TABS.BLOG, label: t("tabs.blog") },
    { id: FINAL_REVIEW_TABS.CAPTION, label: t("tabs.caption") },
    { id: FINAL_REVIEW_TABS.QUALITY, label: t("tabs.quality") },
  ];

  return (
    <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
      <p className="font-medium">{t("title")}</p>
      <div className="flex flex-wrap gap-1" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            className={cn(
              "rounded-md border px-3 py-1 text-xs transition-colors",
              activeTab === tab.id
                ? "border-[var(--color-primary)] bg-[var(--color-primary)] text-white"
                : "border-[var(--color-border)] text-[var(--color-text-muted)]",
            )}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div role="tabpanel">
        {activeTab === FINAL_REVIEW_TABS.CAROUSEL && (
          <ContentPhaseReview state={state} editable={false} />
        )}
        {activeTab === FINAL_REVIEW_TABS.BLOG && (
          <BlogPreviewPanel
            loading={previewLoading}
            error={previewError}
            markdown={displayedBlogMarkdown}
            loadingText={t("blogPreviewLoading")}
            placeholderText={t("blogPlaceholder")}
          />
        )}
        {activeTab === FINAL_REVIEW_TABS.CAPTION && (
          <div className="space-y-2">
            {caption ? (
              <p className="whitespace-pre-wrap text-[var(--color-text-muted)]">
                {caption}
              </p>
            ) : (
              <p className="text-[var(--color-text-muted)]">
                {t("captionEmpty")}
              </p>
            )}
          </div>
        )}
        {activeTab === FINAL_REVIEW_TABS.QUALITY && (
          <div className="space-y-2">
            {scoreEntries.length > 0 ? (
              <ul className="space-y-1">
                {scoreEntries.map(([name, value]) => (
                  <li
                    key={name}
                    className="flex items-center justify-between gap-2 text-[var(--color-text-muted)]"
                  >
                    <span className="font-medium capitalize">
                      {name.replaceAll("_", " ")}
                    </span>
                    <span>
                      {typeof value === "string"
                        ? value
                        : JSON.stringify(value)}
                    </span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[var(--color-text-muted)]">
                {t("qualityEmpty")}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
