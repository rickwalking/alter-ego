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
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import {
  draftText,
  outlineTitle,
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

export function CreateFinalReviewTabs({
  projectId,
  state,
}: FinalReviewTabsProps): React.JSX.Element {
  const tReview = useTranslations("editorialWorkflow.review");
  const t = useTranslations("editorialWorkflow.review.finalReview");
  const untitledSlide = tReview("untitledSlide");
  const [activeTab, setActiveTab] = useState<FinalReviewTab>(
    FINAL_REVIEW_TABS.CAROUSEL,
  );
  const [previewMarkdown, setPreviewMarkdown] = useState<string | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState<string | null>(null);
  const caption = resolveCaption(state);
  const blogMarkdown = resolveBlogMarkdown(state);
  const rubricScores = resolveRubricScores(state);
  const scoreEntries = Object.entries(rubricScores);

  const loadBlogPreview = useCallback(async () => {
    setPreviewLoading(true);
    setPreviewError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.CAROUSEL_PREVIEW_BLOG(projectId, DEFAULT_BLOG_LANGUAGE),
      );
      if (!response.ok) {
        setPreviewError(t("blogPreviewError"));
        return;
      }
      const payload = (await response.json()) as PreviewBlogResponse;
      setPreviewMarkdown(payload.markdown ?? "");
    } catch {
      setPreviewError(t("blogPreviewError"));
    } finally {
      setPreviewLoading(false);
    }
  }, [projectId, t]);

  useEffect(() => {
    if (activeTab !== FINAL_REVIEW_TABS.BLOG) {
      return;
    }
    void loadBlogPreview();
  }, [activeTab, loadBlogPreview]);

  const displayedBlogMarkdown =
    previewMarkdown !== null ? previewMarkdown : blogMarkdown;

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
          <div className="space-y-3">
            {state.outline.length > 0 ? (
              <ol className="list-decimal space-y-2 pl-4">
                {state.outline.map((slide, index) => {
                  const title = outlineTitle(slide, untitledSlide);
                  const draft = state.slide_drafts[index];
                  const text = draft ? draftText(draft) : "";
                  return (
                    <li key={`${index}-${title}`} className="space-y-1">
                      <p className="font-medium text-[var(--color-text)]">
                        {title}
                      </p>
                      {text ? (
                        <p className="line-clamp-4 whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
                          {text}
                        </p>
                      ) : null}
                    </li>
                  );
                })}
              </ol>
            ) : (
              <p className="text-[var(--color-text-muted)]">
                {t("carouselEmpty")}
              </p>
            )}
          </div>
        )}
        {activeTab === FINAL_REVIEW_TABS.BLOG && (
          <div className="space-y-2">
            {previewLoading ? (
              <p className="text-[var(--color-text-muted)]">
                {t("blogPreviewLoading")}
              </p>
            ) : previewError ? (
              <p className="text-[var(--color-text-muted)]">{previewError}</p>
            ) : displayedBlogMarkdown ? (
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-[var(--color-surface)] p-3 text-[var(--color-text-muted)] text-xs">
                {displayedBlogMarkdown}
              </pre>
            ) : (
              <p className="text-[var(--color-text-muted)]">
                {t("blogPlaceholder")}
              </p>
            )}
          </div>
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
