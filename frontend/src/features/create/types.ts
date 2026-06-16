import type { FinalReviewSendBackPhase } from "@/constants/editorial-workflow";
import type { LocalizedSlideReview } from "@/modules/publishing";
import type { EditorialWorkflowState } from "@/modules/publishing";

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
  showPublishLink: boolean;
}
