/**
 * Editorial workspace component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type {
  LocalizedSlideReview,
  SlideImagePrompt,
  SlideValidationViolation,
} from "@/modules/editorial/workspace/types-ai";
import type { NeonTextareaProps } from "@/components/atoms/neon-textarea";
import type { SlideFieldErrors } from "@/modules/editorial/workspace/lib/slide-field-errors";
import type { PresentationStructuredItem } from "@/modules/editorial/workspace/lib/presentation-review-utils";
import type { PresentationInsightQuote } from "@/modules/editorial/workspace/lib/presentation-insight-quote";
import type {
  SlideCopyEdit,
  SlideStructuredItemEdit,
} from "@/modules/editorial/workspace/lib/presentation-slide-resolution";

export interface ImagePromptReviewProps {
  prompts: SlideImagePrompt[] | null | undefined;
  readOnly?: boolean;
}

export interface PresentationIconPreviewProps {
  iconName: string;
  className?: string;
}

export interface PresentationStructuredItemsProps {
  items: PresentationStructuredItem[];
  className?: string;
}

/** AE-0407: the ``pov_news`` quote card shown in the content review. */
export interface PresentationInsightQuoteCardProps {
  insight: PresentationInsightQuote;
}

export interface WorkflowFailedCardProps {
  currentPhase: string;
  errorMessage: string | null | undefined;
  onRetry: () => void;
  isRetrying: boolean;
}

/**
 * AE-0314: shared slide-text editor used by both the review-step recovery panel
 * and the publish-page editor (one component, no duplicated editor bodies).
 * ``onStructuredItemChange``/``showBudget`` are opt-in so the design-recovery
 * panel keeps its exact DOM while the publish page enables extras + budget.
 */
export interface SlideCopyEditorProps {
  slides: LocalizedSlideReview[];
  idPrefix: string;
  onCopyChange: (edit: SlideCopyEdit) => void;
  flagged?: Set<number>;
  policyVersion?: string | null;
  showBudget?: boolean;
  onStructuredItemChange?: (edit: SlideStructuredItemEdit) => void;
  /** AE-0403: blocking violations per field (red border + message + aria). */
  fieldErrors?: SlideFieldErrors;
  /** AE-0403: open violations listed at the bottom of each slide form. */
  violations?: SlideValidationViolation[];
}

/** AE-0314: a locale's editable structured-item list (summary points/features). */
export interface StructuredList {
  listKey: string;
  items: Record<string, unknown>[];
}

export interface AutoRepairButtonProps {
  projectId: string;
  /** Refresh workflow state/slides after a repair (and on a run-in-progress 409). */
  onRepaired?: () => void;
  /**
   * Completed carousels chain a republish so the served PDF reflects the fix.
   * The publish page (which owns the publishing context) supplies this — the
   * button stays free of a cross-context import into publishing.
   */
  onRepublishNeeded?: () => void;
}

/** AE-0375: the slide-1 hook picker at the outline gate. */
export interface HookPickerProps {
  projectId: string;
  /** Up to five candidates generated from the owner's thesis. */
  candidates: readonly string[];
  /** The hook currently on slide 1 (the saved pick, else candidate 1). */
  initialHook: string;
  /** False when no thesis word shows up on slides 1-2 (outline check). */
  thesisEarly?: boolean;
}

/** AE-0403: a textarea that shows its own field error (border + aria). */
export interface FlaggableTextareaProps extends NeonTextareaProps {
  id: string;
  violations: SlideValidationViolation[] | undefined;
}

/** AE-0403: the error message rendered under one flagged field. */
export interface FieldErrorMessageProps {
  id: string;
  violations: SlideValidationViolation[] | undefined;
}

/** AE-0403: per-slide summary at the bottom of a slide form. */
export interface SlideViolationSummaryProps {
  slideIndex: number;
  violations: SlideValidationViolation[];
}

/** AE-0403: the global blocking line, linking every slide still flagged. */
export interface BlockingSlidesNoticeProps {
  message: string;
  slideIndexes: number[];
  onSelectSlide: (slideIndex: number) => void;
}
