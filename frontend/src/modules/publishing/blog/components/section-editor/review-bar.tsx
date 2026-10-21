"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import {
  BLOG_EDITOR_I18N_NAMESPACE,
  BLOG_REJECT_REASON_MAX_LENGTH,
} from "@/constants/blog-editor";
import { EditorErrorNotice } from "../editor-error-notice";
import { ScheduleControl } from "./schedule-control";
import type { ReviewBarProps } from "./types";

const REVIEWER_INPUT_ID = "blog-reviewer-id";
const REJECT_INPUT_ID = "blog-reject-reason";
const STATUS = {
  DRAFT: "draft",
  UNDER_REVIEW: "under_review",
  APPROVED: "approved",
  PUBLISHED: "published",
} as const;

/**
 * Review / publish / schedule controls, driven by the post status
 * and the existing workflow guards. A draft offers "Publish now" (the author
 * self-approves) or a submit for review, to an optional distinct
 * reviewer (empty = the author). Publishing a draft is left to the API status
 * guard, whose error is shown here.
 */
export function ReviewBar(props: Readonly<ReviewBarProps>): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const { status, disabled, error } = props;
  return (
    <div className="space-y-3 rounded border p-3" data-testid="review-bar">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold">{t("review.title")}</span>
        <NeonBadge variant="outline">{t(`review.status.${status}`)}</NeonBadge>
      </div>
      <EditorErrorNotice error={error} />
      {status === STATUS.DRAFT && <DraftControls {...props} />}
      {status === STATUS.UNDER_REVIEW && <UnderReviewControls {...props} />}
      {status === STATUS.APPROVED && (
        <div className="space-y-2">
          <NeonButton size="sm" disabled={disabled} onClick={props.onPublish}>
            {t("review.publish")}
          </NeonButton>
          <ScheduleControl
            scheduledPublishAt={props.scheduledPublishAt}
            disabled={disabled}
            onSchedule={props.onSchedule}
            onCancelSchedule={props.onCancelSchedule}
          />
        </div>
      )}
      {status === STATUS.PUBLISHED && (
        <NeonButton
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={props.onUnpublish}
        >
          {t("review.unpublish")}
        </NeonButton>
      )}
    </div>
  );
}

function DraftControls(props: Readonly<ReviewBarProps>): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const [reviewerId, setReviewerId] = useState("");
  const { disabled } = props;
  const reviewer = reviewerId.trim();
  return (
    <div className="space-y-2">
      <NeonButton size="sm" disabled={disabled} onClick={props.onPublishNow}>
        {t("review.publishNow")}
      </NeonButton>
      <div>
        <label
          htmlFor={REVIEWER_INPUT_ID}
          className="mb-1 block text-xs font-semibold text-text-muted"
        >
          {t("review.reviewer")}
        </label>
        <NeonInput
          id={REVIEWER_INPUT_ID}
          value={reviewerId}
          disabled={disabled}
          onChange={(e) => setReviewerId(e.target.value)}
        />
        <p className="mt-1 text-xs text-text-muted">
          {t("review.reviewerHint")}
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        <NeonButton
          size="sm"
          variant="secondary"
          disabled={disabled}
          onClick={() => props.onSubmitReview(reviewer || null)}
        >
          {t("review.submit")}
        </NeonButton>
        <NeonButton
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={props.onPublish}
        >
          {t("review.publish")}
        </NeonButton>
      </div>
    </div>
  );
}

function UnderReviewControls(
  props: Readonly<ReviewBarProps>,
): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const [reason, setReason] = useState("");
  const { disabled } = props;
  return (
    <div className="space-y-2">
      <NeonButton size="sm" disabled={disabled} onClick={props.onApprove}>
        {t("review.approve")}
      </NeonButton>
      <div>
        <label
          htmlFor={REJECT_INPUT_ID}
          className="mb-1 block text-xs font-semibold text-text-muted"
        >
          {t("review.rejectReason")}
        </label>
        <NeonInput
          id={REJECT_INPUT_ID}
          value={reason}
          maxLength={BLOG_REJECT_REASON_MAX_LENGTH}
          disabled={disabled}
          onChange={(e) => setReason(e.target.value)}
        />
      </div>
      <NeonButton
        size="sm"
        variant="outline"
        disabled={disabled || !reason.trim()}
        onClick={() => props.onReject(reason.trim())}
      >
        {t("review.reject")}
      </NeonButton>
    </div>
  );
}
