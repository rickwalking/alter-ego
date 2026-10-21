"use client";

import {
  AiSuggestionPanel,
  ReviewBar,
  VersionHistorySidebar,
  VoiceScore,
  activeDocument,
  snapshotText,
} from "@/modules/publishing";
import type { BlogEditorSidebarProps } from "@/app/dashboard/blog-posts/types";

/**
 * Right column of the blog editor: review/publish/schedule, the
 * voice score of the shown language, version history and the AI panel. The
 * workflow controls are disabled while there are unsaved edits.
 */
/** Unsaved edits, a save, a review action or a slot action in flight. */
function editorIsBusy({
  editor,
  review,
  slotsPending,
}: Pick<
  BlogEditorSidebarProps,
  "editor" | "review" | "slotsPending"
>): boolean {
  return editor.dirty || editor.saving || review.pending || slotsPending;
}

/**
 * The workflow controls stay busy while a slot action runs, because it may
 * change the content and reset the review.
 */
export function BlogEditorSidebar({
  editor,
  review,
  data,
  selection,
  slotsPending,
  onApplySuggestion,
}: Readonly<BlogEditorSidebarProps>): React.ReactElement | null {
  const { post, draft } = editor;
  if (!post || !draft) {
    return null;
  }
  const shown = activeDocument(draft.document, editor.language);
  const busy = editorIsBusy({ editor, review, slotsPending });
  return (
    <div className="space-y-4">
      <ReviewBar
        status={post.status}
        scheduledPublishAt={post.scheduled_publish_at ?? null}
        disabled={busy}
        error={review.error}
        onSubmitReview={(reviewerId) => void review.submitForReview(reviewerId)}
        onApprove={() => void review.approve()}
        onReject={(reason) => void review.reject(reason)}
        onPublish={() => void review.publish()}
        onPublishNow={() => void review.publishNow()}
        onUnpublish={() => void review.unpublish()}
        onSchedule={(iso) => void review.schedule(iso)}
        onCancelSchedule={() => void review.cancelSchedule()}
      />
      <VoiceScore
        quality={shown?.quality ?? null}
        personas={data.personas}
        personaId={data.personaId}
        onPersonaChange={data.setPersonaId}
      />
      <VersionHistorySidebar
        versions={data.versions}
        loading={data.versionsLoading}
        currentText={snapshotText(draft.document)}
        disabled={busy}
        onRestore={(versionNumber) => editor.handleRestore(versionNumber)}
      />
      <AiSuggestionPanel
        postId={post.id}
        selectedText={selection?.text ?? ""}
        personaId={data.personaId ?? undefined}
        onApplySuggestion={onApplySuggestion}
      />
    </div>
  );
}
