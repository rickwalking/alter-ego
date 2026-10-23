import type { FinalReviewSendBackPhase } from "@/constants/editorial-workflow";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";

/** The revise feedback box and the final-review send-back target. */
export interface WorkflowFeedback {
  feedback: string;
  setFeedback: (value: string) => void;
  feedbackError: string | null;
  setFeedbackError: (value: string | null) => void;
  sendBackTarget: FinalReviewSendBackPhase;
  setSendBackTarget: (value: FinalReviewSendBackPhase) => void;
  handleRevise: () => void;
}

export interface CreateWorkflowControlsProps extends WorkflowFeedback {
  state: EditorialWorkflowState | null;
  showLiveControls: boolean;
  loading: boolean;
  approve: (options?: object) => void;
  contentHasEdits: boolean;
  contentSlides: LocalizedSlideReview[];
  personaApproveBlocked: boolean;
  /** Which slides are under the voice threshold, with scores. */
  personaShortfallDetail?: string | null;
  presentationApproveBlocked: boolean;
  editBudgetBlocked: boolean;
  /** Plain revise is a no-op while the design step is blocking. */
  designReviseBlocked: boolean;
  showPublishLink: boolean;
  /**
   * Final review: a caption / LinkedIn edit is unsaved or still saving, so
   * approve and send back wait (they would drop it or send a stale lock).
   */
  copyBlocked?: boolean;
}
