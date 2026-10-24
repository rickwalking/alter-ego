/**
 * Editorial workspace component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type {
  LocalizedSlideReview,
  SlideImagePrompt,
  SlideValidationViolation,
} from "@/modules/editorial/workspace/types-ai";
import type { NeonTextareaProps } from "@/components/atoms/neon-textarea";
import type { CoverIdeaSource } from "@/constants/cover-prompt-ideas";
import type { CoverIdeasPalette } from "@/schemas/cover-prompt-ideas";
import type { SlideFieldErrors } from "@/modules/editorial/workspace/lib/slide-field-errors";
import type { PresentationStructuredItem } from "@/modules/editorial/workspace/lib/presentation-review-utils";
import type { PresentationInsightQuote } from "@/modules/editorial/workspace/lib/presentation-insight-quote";
import type { RepairSlideDiff } from "@/modules/editorial/workspace/hooks/use-repair-carousel";
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

/** The ``pov_news`` quote card shown in the content review. */
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
 * Shared slide-text editor used by both the review-step recovery panel
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
  /** Blocking violations per field (red border + message + aria). */
  fieldErrors?: SlideFieldErrors;
  /** Open violations listed at the bottom of each slide form. */
  violations?: SlideValidationViolation[];
}

/** A locale's editable structured-item list (summary points/features). */
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

/** The slide-1 hook picker at the outline gate. */
export interface HookPickerProps {
  projectId: string;
  /** Up to five candidates generated from the owner's thesis. */
  candidates: readonly string[];
  /** The hook currently on slide 1 (the saved pick, else candidate 1). */
  initialHook: string;
  /** False when no thesis word shows up on slides 1-2 (outline check). */
  thesisEarly?: boolean;
}

/** A textarea that shows its own field error (border + aria). */
export interface FlaggableTextareaProps extends NeonTextareaProps {
  id: string;
  violations: SlideValidationViolation[] | undefined;
}

/** The error message rendered under one flagged field. */
export interface FieldErrorMessageProps {
  id: string;
  violations: SlideValidationViolation[] | undefined;
}

/** Per-slide summary at the bottom of a slide form. */
export interface SlideViolationSummaryProps {
  slideIndex: number;
  violations: SlideValidationViolation[];
}

/** The global blocking line, linking every slide still flagged. */
export interface BlockingSlidesNoticeProps {
  message: string;
  slideIndexes: number[];
  onSelectSlide: (slideIndex: number) => void;
}

/** What one auto-repair fixed and how many blockers it left. */
export interface RepairOutcome {
  fixed: RepairSlideDiff[];
  remaining: number;
}

/** The suggestion list of a cover-photo prompt field. */
export interface CoverPromptIdeasProps {
  ideas: readonly string[];
  source: CoverIdeaSource;
  onPick: (idea: string) => void;
  onMore: () => void;
  canAskMore: boolean;
  loadingMore: boolean;
  moreFailed: boolean;
}

/** A cover-photo prompt field with its curated and AI suggestions. */
export interface CoverPromptFieldProps {
  id: string;
  topic: string;
  palette: CoverIdeasPalette | null;
  value: string;
  onChange: (value: string) => void;
}

/** The suggestions of a cover prompt: the carousel topic and palette, and what a tap fills. */
export interface CoverPromptSuggestionsProps {
  topic: string;
  palette: CoverIdeasPalette | null;
  onPick: (prompt: string) => void;
}

/** The copy button of the cover-photo prompt. */
export interface CoverPromptCopyProps {
  text: string;
}

/** AI ideas of the cover-photo prompt and the topic/palette key they answer. */
export interface CoverAiIdeas {
  context: string;
  ideas: readonly string[];
}
