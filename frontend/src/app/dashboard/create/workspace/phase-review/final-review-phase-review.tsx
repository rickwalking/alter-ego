"use client";

import { CreateFinalReviewTabs } from "../create-final-review-tabs";
import type { EditorialWorkflowState } from "@/modules/publishing";

export interface FinalReviewPhaseReviewProps {
  projectId: string;
  state: EditorialWorkflowState;
  /** Refetch the workflow state after a caption / LinkedIn save. */
  onCopySaved?: () => Promise<unknown>;
}

const noRefresh = (): Promise<unknown> => Promise.resolve();

export function FinalReviewPhaseReview({
  projectId,
  state,
  onCopySaved = noRefresh,
}: Readonly<FinalReviewPhaseReviewProps>): React.ReactElement {
  return (
    <CreateFinalReviewTabs
      projectId={projectId}
      state={state}
      onCopySaved={onCopySaved}
    />
  );
}
