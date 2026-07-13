import type { FinalReviewSendBackPhase } from "@/constants/editorial-workflow";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import type { EditorialWorkflowState } from "@/modules/editorial/workspace/types-ai";

export interface CreateWorkflowControlsProps {
  state: EditorialWorkflowState | null;
  showLiveControls: boolean;
  loading: boolean;
  feedback: string;
  setFeedback: (value: string) => void;
  feedbackError: string | null;
  setFeedbackError: (value: string | null) => void;
  sendBackTarget: FinalReviewSendBackPhase;
  setSendBackTarget: (value: FinalReviewSendBackPhase) => void;
  handleRevise: () => void;
  approve: (options?: object) => void;
  contentHasEdits: boolean;
  contentSlides: LocalizedSlideReview[];
  personaApproveBlocked: boolean;
  presentationApproveBlocked: boolean;
  editBudgetBlocked: boolean;
  /** AE-0310: plain revise is a no-op while the design step is blocking. */
  designReviseBlocked: boolean;
  showPublishLink: boolean;
}
