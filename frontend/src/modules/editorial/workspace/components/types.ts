/**
 * Editorial workspace component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { SlideImagePrompt } from "@/modules/editorial/workspace/types-ai";
import type { PresentationStructuredItem } from "@/modules/editorial/workspace/lib/presentation-review-utils";

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
