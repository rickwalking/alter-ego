/**
 * Distribution component prop/state types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { CarouselProjectResponse } from "@/schemas/carousel";

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
