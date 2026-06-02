"use client";

import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import { ResearchPhaseReview } from "./phase-review/research-phase-review";
import { OutlinePhaseReview } from "./phase-review/outline-phase-review";
import { ContentPhaseReview } from "./phase-review/content-phase-review";
import { DesignPhaseReview } from "./phase-review/design-phase-review";
import { ImagesPhaseReview } from "./phase-review/images-phase-review";
import { FinalReviewPhaseReview } from "./phase-review/final-review-phase-review";

interface EditorialPhaseReviewProps {
  projectId: string;
  state: EditorialWorkflowState;
}

export function CreatePhaseReview({
  projectId,
  state,
}: EditorialPhaseReviewProps): React.JSX.Element | null {
  const phase = state.current_phase;

  switch (phase) {
    case EDITORIAL_PHASES.RESEARCH:
      return <ResearchPhaseReview state={state} />;
    case EDITORIAL_PHASES.OUTLINE:
      return <OutlinePhaseReview state={state} />;
    case EDITORIAL_PHASES.CONTENT:
      return <ContentPhaseReview state={state} />;
    case EDITORIAL_PHASES.DESIGN:
      return <DesignPhaseReview state={state} />;
    case EDITORIAL_PHASES.IMAGES:
      return <ImagesPhaseReview state={state} />;
    case EDITORIAL_PHASES.FINAL_REVIEW:
      return <FinalReviewPhaseReview projectId={projectId} state={state} />;
    default:
      return null;
  }
}
