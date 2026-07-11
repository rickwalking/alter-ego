/**
 * Distribution component prop/state types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { LocalizedSlideReview } from "@/modules/publishing/blog/types-ai";

export interface CaptionEditorProps {
  value: string;
  onChange: (value: string) => void;
  maxChars: number;
  placeholder: string;
  ariaLabel: string;
  helpText?: string;
}

export interface HorizontalCarouselViewerProps {
  slideUrls: string[];
  alt: string;
}

export interface PublishFailedNoticeProps {
  currentPhase: string;
  errorMessage: string | null | undefined;
  workspaceHref: string;
}

export interface EditorState {
  seed: string;
  caption: string;
  linkedinPt: string;
  linkedinEn: string;
}

export interface PublishPanelProps {
  project: CarouselProjectResponse;
  onPublishInstagram?: (caption: string) => Promise<void>;
  isPublishingInstagram?: boolean;
  publishResult?: { status: "idle" | "success" | "error"; message?: string };
  // AE-0313: extra cache-buster (the freshly built artifact version) appended
  // to PDF/slide URLs after a "Rebuild PDF" so the browser fetches the new
  // artifact rather than a cached prior version.
  cacheBustToken?: string;
}

export interface RebuildPdfSectionProps {
  projectId: string;
  onRebuilt: (artifactVersion: string | null) => void;
}

/**
 * AE-0314: publish-page text editor for a completed carousel. Reuses the shared
 * ``SlideCopyEditor``; on save it PATCHes the slides then chains the republish so
 * the served PDF reflects the edit (images never regenerate).
 */
export interface SlideTextEditSectionProps {
  projectId: string;
  slides: LocalizedSlideReview[];
  policyVersion?: string | null;
  /** True while a workflow run is in progress — editing is blocked. */
  runInProgress: boolean;
  /** True while a server-guaranteed rebuild is still owed (marker set). */
  rebuildPending?: boolean;
  /** Refetch project + workflow state after a successful edit + republish. */
  onEdited: () => void;
}
