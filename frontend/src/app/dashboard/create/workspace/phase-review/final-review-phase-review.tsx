"use client";

import { CreateFinalReviewTabs } from "../create-final-review-tabs";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";

export interface FinalReviewPhaseReviewProps {
  projectId: string;
  state: EditorialWorkflowState;
}

export function FinalReviewPhaseReview({
  projectId,
  state,
}: FinalReviewPhaseReviewProps): React.ReactElement {
  return <CreateFinalReviewTabs projectId={projectId} state={state} />;
}
