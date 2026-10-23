"use client";

import { CreateFinalReviewTabs } from "../create-final-review-tabs";
import type { EditorialWorkflowState } from "@/modules/publishing";

export interface FinalReviewPhaseReviewProps {
  projectId: string;
  state: EditorialWorkflowState;
  /** Refetch the workflow state after a caption / LinkedIn save. */
  onCopySaved?: () => Promise<unknown>;
  /** Told whether a caption / LinkedIn edit is unsaved or saving. */
  onCopyBusyChange?: (busy: boolean) => void;
}

const noRefresh = (): Promise<unknown> => Promise.resolve();

export function FinalReviewPhaseReview({
  projectId,
  state,
  onCopySaved = noRefresh,
  onCopyBusyChange,
}: Readonly<FinalReviewPhaseReviewProps>): React.ReactElement {
  return (
    <CreateFinalReviewTabs
      projectId={projectId}
      state={state}
      onCopySaved={onCopySaved}
      onCopyBusyChange={onCopyBusyChange}
    />
  );
}
