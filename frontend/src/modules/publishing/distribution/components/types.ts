import type { ViewerLanguage } from "@/modules/publishing/distribution/types";
/**
 * Distribution component prop/state types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { usePickCover } from "@/modules/publishing/distribution/hooks/use-cover-picker";
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
  /**
   * Extra cache-buster (the freshly built artifact version) appended to
   * PDF/slide URLs after a "Rebuild PDF" so the browser fetches the new
   * artifact rather than a cached prior version.
   */
  cacheBustToken?: string;
  /** 1-based numbers of the real slides; the viewer counts these. */
  slideNumbers?: readonly number[];
}

/** One slide-1 cover option (library photo or GrokBot offer). */
export interface CoverOptionView {
  asset_id: string;
  source: "library" | "offer";
  kind?: string;
}

export interface CoverOptionGridProps {
  options: readonly CoverOptionView[];
  currentAssetId: string | null;
  disabled: boolean;
  onChoose: (assetId: string) => void;
}

export interface CoverThumbProps {
  option: CoverOptionView;
  number: number;
  current: boolean;
  disabled: boolean;
  onChoose: (assetId: string) => void;
}

/**
 * Publish-page "Capa (slide 1)" for a Ponto de Vista carousel. A pick
 * re-renders slides + PDFs server-side at the current workflow lock version;
 * ``onSwitched`` receives the fresh artifact version (cache-bust + refetch).
 */
export interface CoverPickerSectionProps {
  projectId: string;
  onSwitched: (artifactVersion: string | null) => void;
}

export interface RebuildPdfSectionProps {
  projectId: string;
  onRebuilt: (artifactVersion: string | null) => void;
}

/**
 * Publish-page text editor for a completed carousel. Reuses the shared
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

export interface CoverPickDeps {
  projectId: string;
  currentAssetId: string | null;
  onSwitched: CoverPickerSectionProps["onSwitched"];
}

export interface PickStatusProps {
  pending: boolean;
  switched: boolean;
  switchingText: string;
  successText: string;
}

export interface CoverPick {
  pick: ReturnType<typeof usePickCover>;
  switched: boolean;
  handleChoose: (assetId: string) => void;
}

/** Save/cancel buttons of the publish-page slide text editor (AE-0446). */
export interface SlideEditActionsProps {
  refused: boolean;
  canSave: boolean;
  saving: boolean;
  onSave: () => void;
  onCancel: () => void;
}

/** Rebuild/success line of the publish-page slide text editor (AE-0446). */
export interface SlideEditStatusProps {
  pending: boolean;
  done: boolean;
}

/** PT / EN tab strip of the publish panel (AE-0446). */
export interface LanguageTabsProps {
  language: ViewerLanguage;
  onChange: (language: ViewerLanguage) => void;
  ariaLabel: string;
  className: string;
}

/** Instagram tab of the publish panel (AE-0446). */
export interface InstagramTabProps extends Pick<
  PublishPanelProps,
  "onPublishInstagram" | "isPublishingInstagram" | "publishResult"
> {
  caption: string;
  onCaptionChange: (caption: string) => void;
  language: ViewerLanguage;
}

/** LinkedIn tab of the publish panel (AE-0446). */
export interface LinkedInTabProps {
  text: string;
  onTextChange: (text: string) => void;
  language: ViewerLanguage;
  setLanguage: (language: ViewerLanguage) => void;
  pdfHref: string;
}
