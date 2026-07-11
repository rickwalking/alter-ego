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
} from "@/modules/editorial/workspace/types-ai";
import type { PresentationStructuredItem } from "@/modules/editorial/workspace/lib/presentation-review-utils";
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
