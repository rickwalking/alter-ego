"use client";
import { NeonAlert, NeonAlertDescription } from "@/components/molecules/neon-alert";

import { useTranslations } from "next-intl";
import { ReviewAssignmentPanel } from "@/features/workflow/components/review-assignment-panel";
import { ScheduledPublishPicker } from "@/features/workflow/components/scheduled-publish-picker";
import { VersionDiffView } from "@/features/workflow/components/version-diff-view";
import { useCollaborativeEdit } from "@/features/workflow/hooks/use-collaborative-edit";
import { LOCK_CONTENT_TYPE_BLOG } from "@/constants/workflow";

type BlogPostEditExtrasProps = {
  postId: string;
  title: string;
  status: string;
  bodyText: string;
  previousBodyText?: string;
  onScheduled?: () => void;
};

export function BlogPostEditExtras({
  postId,
  title,
  status,
  bodyText,
  previousBodyText,
  onScheduled,
}: BlogPostEditExtrasProps) {
  const t = useTranslations("workflow");
  const { activeLock, isLockedByOther } = useCollaborativeEdit(
    postId,
    LOCK_CONTENT_TYPE_BLOG,
  );

  return (
    <div className="space-y-4 border-t pt-4">
      {isLockedByOther && activeLock && (
        <NeonAlert>
          <NeonAlertDescription>
            {t("collaboration.lockedByOther", { name: activeLock.user_name })}
          </NeonAlertDescription>
        </NeonAlert>
      )}
      <ReviewAssignmentPanel
        contentId={postId}
        contentType={LOCK_CONTENT_TYPE_BLOG}
        title={title}
      />
      {status === "approved" && (
        <ScheduledPublishPicker postId={postId} onScheduled={onScheduled} />
      )}
      {previousBodyText && previousBodyText !== bodyText && (
        <VersionDiffView
          leftLabel={t("diff.previousVersion")}
          rightLabel={t("diff.currentDraft")}
          leftText={previousBodyText}
          rightText={bodyText}
        />
      )}
    </div>
  );
}
