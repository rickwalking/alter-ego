/**
 * Editorial workflow component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { CarouselReprocessCapability } from "@/schemas/carousel-reprocess";

export interface BlogPostEditExtrasProps {
  postId: string;
  title: string;
  status: string;
  bodyText: string;
  previousBodyText?: string;
  onScheduled?: () => void;
}

export interface ReviewAssignmentPanelProps {
  contentId: string;
  contentType: string;
  title: string;
  onAssigned?: () => void;
}

export interface ScheduledPublishPickerProps {
  postId: string;
  onScheduled?: () => void;
}

export interface VersionDiffViewProps {
  leftLabel: string;
  rightLabel: string;
  leftText: string;
  rightText: string;
}

export interface CarouselReprocessProps {
  capability: CarouselReprocessCapability | null;
  pending: boolean;
  canSubmit: boolean;
  error: string | null;
  onReprocess: () => void;
}

export interface CarouselReprocessProgressProps {
  capability: CarouselReprocessCapability;
}

export interface CarouselReprocessActionProps {
  capability: CarouselReprocessCapability;
  pending: boolean;
  canSubmit: boolean;
  onReprocess: () => void;
}
