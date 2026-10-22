"use client";

import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/publishing";
import { AutoRepairButton } from "@/modules/editorial";
import { ResearchPhaseReview } from "./phase-review/research-phase-review";
import { OutlinePhaseReview } from "./phase-review/outline-phase-review";
import {
  ContentPhaseReview,
  type ContentManualFixesActions,
} from "./phase-review/content-phase-review";
import { DesignPhaseReview } from "./phase-review/design-phase-review";
import type { DesignRecoveryActions } from "./phase-review/design-recovery-panel";
import { ImagesPhaseReview } from "./phase-review/images-phase-review";
import { FinalReviewPhaseReview } from "./phase-review/final-review-phase-review";

interface EditorialPhaseReviewProps {
  projectId: string;
  state: EditorialWorkflowState;
  contentSlides?: LocalizedSlideReview[];
  onContentSlidesChange?: (slides: LocalizedSlideReview[]) => void;
  contentEditable?: boolean;
  /** Save content-gate edits without approving (edits-only revise). */
  contentManualFixes?: ContentManualFixesActions;
  /** Design-step recovery actions (edit copy / send back). */
  designRecovery?: DesignRecoveryActions;
  /** Refresh workflow state after a one-click deterministic repair. */
  onRepaired?: () => void;
  /** A run is executing — no auto-fix (it would 409). */
  actionsLocked?: boolean;
  /** Refetch the workflow state after a final-review caption / LinkedIn save. */
  onCopySaved?: () => Promise<unknown>;
}

export function CreatePhaseReview({
  projectId,
  state,
  contentSlides,
  onContentSlidesChange,
  contentEditable = false,
  contentManualFixes,
  designRecovery,
  onRepaired,
  actionsLocked = false,
  onCopySaved,
}: Readonly<EditorialPhaseReviewProps>): React.JSX.Element | null {
  const phase = state.current_phase;
  const autoRepair = actionsLocked ? null : (
    <AutoRepairButton projectId={projectId} onRepaired={onRepaired} />
  );

  switch (phase) {
    case EDITORIAL_PHASES.RESEARCH:
      return <ResearchPhaseReview state={state} />;
    case EDITORIAL_PHASES.OUTLINE:
      return <OutlinePhaseReview state={state} projectId={projectId} />;
    case EDITORIAL_PHASES.CONTENT:
      return (
        <div className="space-y-3">
          <ContentPhaseReview
            state={state}
            editable={contentEditable}
            slides={contentSlides}
            onSlidesChange={onContentSlidesChange}
            manualFixes={contentManualFixes}
          />
          {autoRepair}
        </div>
      );
    case EDITORIAL_PHASES.DESIGN:
      return (
        <div className="space-y-3">
          <DesignPhaseReview state={state} recovery={designRecovery} />
          {autoRepair}
        </div>
      );
    case EDITORIAL_PHASES.IMAGES:
      return <ImagesPhaseReview state={state} />;
    case EDITORIAL_PHASES.FINAL_REVIEW:
      return (
        <FinalReviewPhaseReview
          projectId={projectId}
          state={state}
          onCopySaved={onCopySaved}
        />
      );
    default:
      return null;
  }
}
