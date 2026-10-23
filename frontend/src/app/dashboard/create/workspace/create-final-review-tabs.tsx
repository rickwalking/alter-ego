"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { cn } from "@/lib/utils";
import {
  FINAL_REVIEW_TABS,
  type FinalReviewTab,
} from "@/constants/editorial-workflow";
import {
  ReviewCaptionEditor,
  ReviewCopyLeaveGuard,
  ReviewLinkedInEditor,
  COPY_FIELDS,
  type EditorialWorkflowState,
} from "@/modules/publishing";
import { ContentPhaseReview } from "@/app/dashboard/create/workspace/phase-review/content-phase-review";
import { FinalReviewBlogTab } from "./phase-review/final-review-blog-tab";
import {
  useFinalReviewCopy,
  useReportCopyBusy,
  type FinalReviewCopy,
} from "./phase-review/use-final-review-copy";
import {
  resolveBlogMarkdown,
  resolveRubricScores,
} from "./create-phase-review-helpers";

interface FinalReviewTabsProps {
  projectId: string;
  state: EditorialWorkflowState;
  /** Refetch the workflow state after a caption / LinkedIn save. */
  onCopySaved: () => Promise<unknown>;
  /** Told whether a caption / LinkedIn edit is unsaved or saving. */
  onCopyBusyChange?: (busy: boolean) => void;
}

const MUTED = "text-[var(--color-text-muted)]";

/** The caption or a LinkedIn post has edits that are not saved yet. */
function copyUnsaved(copy: FinalReviewCopy): boolean {
  return copy.editor?.isDirty(COPY_FIELDS) === true;
}

interface QualityTabProps {
  readonly state: EditorialWorkflowState;
  readonly emptyText: string;
}

/** The final review rubric scores, or the empty note. */
function QualityTab({ state, emptyText }: QualityTabProps): React.JSX.Element {
  const scoreEntries = Object.entries(resolveRubricScores(state));
  if (scoreEntries.length === 0) {
    return <p className={MUTED}>{emptyText}</p>;
  }
  return (
    <ul className="space-y-1">
      {scoreEntries.map(([name, value]) => (
        <li
          key={name}
          className={cn("flex items-center justify-between gap-2", MUTED)}
        >
          <span className="font-medium capitalize">
            {name.replaceAll("_", " ")}
          </span>
          <span>
            {typeof value === "string" ? value : JSON.stringify(value)}
          </span>
        </li>
      ))}
    </ul>
  );
}

interface CopyTabProps {
  readonly copy: FinalReviewCopy;
  readonly tab: FinalReviewTab;
}

interface CopyPendingProps {
  readonly copy: FinalReviewCopy;
}

/** Why there is no editor yet: still loading, or a failed load with a retry. */
function CopyPending({ copy }: CopyPendingProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.review.finalReview");
  if (!copy.loadFailed) {
    return <p className={MUTED}>{t("copyLoading")}</p>;
  }
  return (
    <div className="space-y-2">
      <p role="alert" className="text-destructive">
        {t("copyLoadFailed")}
      </p>
      <button
        type="button"
        onClick={copy.retry}
        className="rounded-md border border-[var(--color-border)] px-3 py-1 text-xs"
      >
        {t("copyRetry")}
      </button>
    </div>
  );
}

/** The caption or LinkedIn editor, once the saved project texts loaded. */
function CopyTab({ copy, tab }: CopyTabProps): React.JSX.Element {
  if (!copy.editor) {
    return <CopyPending copy={copy} />;
  }
  return tab === FINAL_REVIEW_TABS.CAPTION ? (
    <ReviewCaptionEditor editor={copy.editor} history={copy.history} />
  ) : (
    <ReviewLinkedInEditor editor={copy.editor} history={copy.history} />
  );
}

/**
 * The final review: carousel, blog preview (edited in the blog editor),
 * the editable caption and LinkedIn posts, and the quality scores. The text
 * editor lives here, above the tab switch, so drafts survive a tab change.
 */
export function CreateFinalReviewTabs({
  projectId,
  state,
  onCopySaved,
  onCopyBusyChange,
}: Readonly<FinalReviewTabsProps>): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.review.finalReview");
  const [activeTab, setActiveTab] = useState<FinalReviewTab>(
    FINAL_REVIEW_TABS.CAROUSEL,
  );
  const copy = useFinalReviewCopy(projectId, state, onCopySaved);
  useReportCopyBusy(copy, onCopyBusyChange);

  const tabs: { id: FinalReviewTab; label: string }[] = [
    { id: FINAL_REVIEW_TABS.CAROUSEL, label: t("tabs.carousel") },
    { id: FINAL_REVIEW_TABS.BLOG, label: t("tabs.blog") },
    { id: FINAL_REVIEW_TABS.CAPTION, label: t("tabs.caption") },
    { id: FINAL_REVIEW_TABS.LINKEDIN, label: t("tabs.linkedin") },
    { id: FINAL_REVIEW_TABS.QUALITY, label: t("tabs.quality") },
  ];
  const copyTab =
    activeTab === FINAL_REVIEW_TABS.CAPTION ||
    activeTab === FINAL_REVIEW_TABS.LINKEDIN;

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
                : cn("border-[var(--color-border)]", MUTED),
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
          <FinalReviewBlogTab
            projectId={projectId}
            fallbackMarkdown={resolveBlogMarkdown(state)}
            copyUnsaved={copyUnsaved(copy)}
          />
        )}
        {copyTab && <CopyTab copy={copy} tab={activeTab} />}
        {activeTab === FINAL_REVIEW_TABS.QUALITY && (
          <QualityTab state={state} emptyText={t("qualityEmpty")} />
        )}
      </div>
      {copy.editor && <ReviewCopyLeaveGuard editor={copy.editor} />}
    </div>
  );
}
