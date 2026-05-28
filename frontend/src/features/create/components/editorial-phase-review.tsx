"use client";

import { useCallback, useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  API_ENDPOINTS,
  DEFAULT_BLOG_LANGUAGE,
} from "@/constants/api";
import { cn } from "@/lib/utils";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  EDITORIAL_PHASES,
  FINAL_REVIEW_TABS,
  type FinalReviewTab,
} from "@/constants/editorial-workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

interface EditorialPhaseReviewProps {
  projectId: string;
  state: EditorialWorkflowState;
}

function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function outlineTitle(
  slide: Record<string, unknown>,
  fallback: string,
): string {
  return asString(slide.title) || asString(slide.heading) || fallback;
}

function draftText(slide: Record<string, unknown>): string {
  return asString(slide.draft_text) || asString(slide.body) || "";
}

function readProgressField(
  state: EditorialWorkflowState,
  key: string,
): unknown {
  return state.phase_progress?.[key];
}

function resolveCaption(state: EditorialWorkflowState): string {
  return state.caption ?? asString(readProgressField(state, "caption"));
}

function resolveBlogMarkdown(state: EditorialWorkflowState): string {
  return (
    state.blog_markdown ?? asString(readProgressField(state, "blog_markdown"))
  );
}

function resolveRubricScores(
  state: EditorialWorkflowState,
): Record<string, unknown> {
  if (state.rubric_scores && Object.keys(state.rubric_scores).length > 0) {
    return state.rubric_scores;
  }
  const fromProgress = readProgressField(state, "rubric_scores");
  if (fromProgress && typeof fromProgress === "object") {
    return fromProgress as Record<string, unknown>;
  }
  return {};
}

interface FinalReviewTabsProps {
  projectId: string;
  state: EditorialWorkflowState;
}

interface PreviewBlogResponse {
  markdown?: string;
}

function FinalReviewTabs({ projectId, state }: FinalReviewTabsProps): React.JSX.Element {
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
                      <p className="font-medium text-[var(--color-text)]">{title}</p>
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
              <p className="text-[var(--color-text-muted)]">{t("carouselEmpty")}</p>
            )}
          </div>
        )}
        {activeTab === FINAL_REVIEW_TABS.BLOG && (
          <div className="space-y-2">
            {previewLoading ? (
              <p className="text-[var(--color-text-muted)]">{t("blogPreviewLoading")}</p>
            ) : previewError ? (
              <p className="text-[var(--color-text-muted)]">{previewError}</p>
            ) : displayedBlogMarkdown ? (
              <pre className="max-h-64 overflow-auto whitespace-pre-wrap rounded-md bg-[var(--color-surface)] p-3 text-[var(--color-text-muted)] text-xs">
                {displayedBlogMarkdown}
              </pre>
            ) : (
              <p className="text-[var(--color-text-muted)]">{t("blogPlaceholder")}</p>
            )}
          </div>
        )}
        {activeTab === FINAL_REVIEW_TABS.CAPTION && (
          <div className="space-y-2">
            {caption ? (
              <p className="whitespace-pre-wrap text-[var(--color-text-muted)]">{caption}</p>
            ) : (
              <p className="text-[var(--color-text-muted)]">{t("captionEmpty")}</p>
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
                    <span className="font-medium capitalize">{name.replaceAll("_", " ")}</span>
                    <span>{asString(value) || JSON.stringify(value)}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-[var(--color-text-muted)]">{t("qualityEmpty")}</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export function EditorialPhaseReview({
  projectId,
  state,
}: EditorialPhaseReviewProps): React.JSX.Element | null {
  const t = useTranslations("editorialWorkflow.review");
  const untitledSlide = t("untitledSlide");
  const phase = state.current_phase;

  if (phase === EDITORIAL_PHASES.RESEARCH && state.research_findings.length > 0) {
    return (
      <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("researchTitle")}</p>
        <ul className="space-y-2">
          {state.research_findings.map((finding, index) => {
            const source = asString(finding.source) || t("findingFallback", { index: index + 1 });
            const points = Array.isArray(finding.key_points)
              ? finding.key_points.filter((p): p is string => typeof p === "string")
              : [];
            return (
              <li key={source} className="space-y-1">
                <p className="font-medium text-[var(--color-text)]">{source}</p>
                {points.length > 0 ? (
                  <ul className="list-disc space-y-0.5 pl-4 text-[var(--color-text-muted)]">
                    {points.map((point) => (
                      <li key={point}>{point}</li>
                    ))}
                  </ul>
                ) : null}
              </li>
            );
          })}
        </ul>
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.OUTLINE && state.outline.length > 0) {
    return (
      <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("outlineTitle")}</p>
        <ol className="list-decimal space-y-2 pl-4">
          {state.outline.map((slide, index) => {
            const title = outlineTitle(slide, untitledSlide);
            const key = `${asString(slide.slide_index) || index}-${title}`;
            const points = Array.isArray(slide.key_points)
              ? slide.key_points.filter((p): p is string => typeof p === "string")
              : [];
            return (
              <li key={key} className="space-y-0.5">
                <p className="font-medium text-[var(--color-text)]">{title}</p>
                {points.length > 0 ? (
                  <p className="text-[var(--color-text-muted)] text-xs">
                    {points.join(" · ")}
                  </p>
                ) : null}
              </li>
            );
          })}
        </ol>
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.CONTENT && state.slide_drafts.length > 0) {
    return (
      <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("contentTitle")}</p>
        <div className="space-y-3">
          {state.slide_drafts.map((slide, index) => {
            const title = outlineTitle(slide, untitledSlide);
            const text = draftText(slide);
            const key = `${asString(slide.slide_index) || index}-${title}`;
            return (
              <div key={key} className="space-y-1 border-[var(--color-border)] border-b pb-2 last:border-0">
                <p className="font-medium text-[var(--color-text)]">{title}</p>
                {text ? (
                  <p className="whitespace-pre-wrap text-[var(--color-text-muted)] text-xs">
                    {text}
                  </p>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.DESIGN) {
    return (
      <div className="space-y-3 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("designTitle")}</p>
        <p className="text-[var(--color-text-muted)]">
          {state.design_applied ? t("designReady") : t("designPending")}
        </p>
        {state.outline.length > 0 ? (
          <div className="space-y-2">
            <p className="font-medium text-[var(--color-text)] text-xs uppercase tracking-wide">
              {t("outlineTitle")}
            </p>
            <ol className="list-decimal space-y-1 pl-4 text-[var(--color-text-muted)]">
              {state.outline.map((slide, index) => {
                const title = outlineTitle(slide, untitledSlide);
                return (
                  <li key={`${index}-${title}`}>{title}</li>
                );
              })}
            </ol>
          </div>
        ) : null}
        {state.slide_drafts.length > 0 ? (
          <div className="space-y-2">
            <p className="font-medium text-[var(--color-text)] text-xs uppercase tracking-wide">
              {t("contentTitle")}
            </p>
            {state.slide_drafts.slice(0, 3).map((slide, index) => {
              const text = draftText(slide);
              if (!text) return null;
              return (
                <p
                  key={`draft-${index}`}
                  className="line-clamp-3 text-[var(--color-text-muted)] text-xs"
                >
                  {text}
                </p>
              );
            })}
          </div>
        ) : null}
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.IMAGES && (state.image_assets?.length ?? 0) > 0) {
    return (
      <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3 text-sm">
        <p className="font-medium">{t("imagesTitle")}</p>
        <ul className="list-disc space-y-1 pl-4 text-[var(--color-text-muted)]">
          {state.image_assets?.map((asset) => (
            <li key={asset} className="break-all font-mono text-xs">
              {asset}
            </li>
          ))}
        </ul>
      </div>
    );
  }

  if (phase === EDITORIAL_PHASES.FINAL_REVIEW) {
    return <FinalReviewTabs projectId={projectId} state={state} />;
  }

  if (
    phase === EDITORIAL_PHASES.OUTLINE ||
    phase === EDITORIAL_PHASES.CONTENT
  ) {
    return (
      <div className="rounded-md border border-dashed border-[var(--color-border)] p-3 text-[var(--color-text-muted)] text-sm">
        {t("emptyPhase")}
      </div>
    );
  }

  return null;
}
