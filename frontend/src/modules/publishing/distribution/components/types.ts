import type { ViewerLanguage } from "@/modules/publishing/distribution/types";
/**
 * Distribution component prop/state types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { ReactNode } from "react";
import type {
  CoverGeneration,
  CoverGenerationInput,
  CoverGenerations,
} from "@/modules/publishing/distribution/hooks/use-cover-generation";
import type {
  CapReason,
  CoverGenerateForm,
  CoverPhotoUpload,
  UploadLibraryPhoto,
} from "@/modules/publishing/distribution/hooks/types";
import type { usePickCover } from "@/modules/publishing/distribution/hooks/use-cover-picker";
import type { LocalizedSlideReview } from "@/modules/publishing/blog/types-ai";
import type {
  CopyEditor,
  CopyHistory,
  CopySaveStatus,
  LeaveGuard,
  SaveCopy,
} from "@/modules/publishing/distribution/hooks/types";

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
  /** Saves caption / LinkedIn edits; without it the texts are not saved. */
  onSaveCopy?: SaveCopy;
  /** The caption / LinkedIn version history shown under the editors. */
  copyHistory?: CopyHistory;
}

/** Save button + state line of one publish-panel text. */
export interface CopySaveBarProps {
  dirty: boolean;
  status: CopySaveStatus;
  /** The text breaks a platform limit, so it cannot be saved. */
  invalid: boolean;
  onSave: () => Promise<void>;
}

/** The publish panel's unsaved-edits dialog. */
export interface LeaveGuardDialogProps {
  guard: LeaveGuard;
}

/** One slide-1 cover option (library photo, Grok-generated cover or GrokBot offer). */
export interface CoverOptionView {
  asset_id: string;
  source: "library" | "generated" | "offer";
  kind?: string;
}

/**
 * Prompt suggestions for the cover prompt, composed by the page (the
 * suggestions live in the editorial module); ``fill`` puts one in the field.
 */
export type RenderPromptSuggestions = (
  fill: (prompt: string) => void,
) => ReactNode;

/**
 * "Gerar capa com Grok": the owner's library photos it may send and, when the
 * page composes it, the library upload behind "Enviar foto".
 */
export interface CoverGeneratePanelProps {
  projectId: string;
  photos: readonly CoverOptionView[];
  renderPromptSuggestions?: RenderPromptSuggestions;
  uploadPhoto?: UploadLibraryPhoto;
}

/** The status line and the confirmation dialog of the generate form. */
export interface CoverGenerateOutcomeProps {
  form: CoverGenerateForm;
}

/** "Enviar foto": a file picker, its progress and the library's refusal. */
export interface CoverPhotoUploadFieldProps {
  upload: CoverPhotoUpload;
  disabled: boolean;
}

/** The library photos as checkboxes (at most ``max`` ticked). */
export interface CoverPhotoChecklistProps {
  photos: readonly CoverOptionView[];
  selected: readonly string[];
  max: number;
  disabled: boolean;
  onToggle: (assetId: string) => void;
}

/** The editable direction of a generated cover; ``children`` sit under it. */
export interface CoverPromptFieldProps {
  value: string;
  onChange: (prompt: string) => void;
  children?: ReactNode;
}

/** The caps in use (null until loaded). */
export interface CoverUsageLineProps {
  usage: CoverGenerations | null;
}

/** The generate button and the cap reason. */
export interface CoverGenerateActionProps {
  enabled: boolean;
  blocked: CapReason;
  onAsk: () => void;
}

/** Why the generate form is not shown. */
export interface CoverGenerateUnavailableProps {
  error: Error;
}

/** The confirmation of one generation. */
export interface CoverGenerateConfirmProps {
  asking: CoverGenerationInput;
  usage: CoverGenerations;
  onConfirm: () => Promise<void>;
  onClose: () => void;
}

/** The running or failed state of the latest generation. */
export interface CoverGenerationStatusProps {
  /** The newest generation (its status, failure code and the Grok Bot's message), or null. */
  generation: CoverGeneration | null;
  canRetry: boolean;
  onRetry: () => void;
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
  renderPromptSuggestions?: RenderPromptSuggestions;
  uploadPhoto?: UploadLibraryPhoto;
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

/** Save/cancel buttons of the publish-page slide text editor. */
export interface SlideEditActionsProps {
  refused: boolean;
  canSave: boolean;
  saving: boolean;
  onSave: () => void;
  onCancel: () => void;
}

/** Rebuild/success line of the publish-page slide text editor. */
export interface SlideEditStatusProps {
  pending: boolean;
  done: boolean;
}

/** Copy-to-clipboard button of a publish-panel text. */
export interface CopyTextButtonProps {
  text: string;
  label: string;
  disabled: boolean;
}

/** PT / EN tab strip of the publish panel. */
export interface LanguageTabsProps {
  language: ViewerLanguage;
  onChange: (language: ViewerLanguage) => void;
  ariaLabel: string;
  className: string;
}

/** Instagram tab of the publish panel. */
export interface InstagramTabProps extends Pick<
  PublishPanelProps,
  "onPublishInstagram" | "isPublishingInstagram" | "publishResult"
> {
  caption: string;
  onCaptionChange: (caption: string) => void;
  language: ViewerLanguage;
  /** Present when saving is wired: the save bar of the caption. */
  save?: Omit<CopySaveBarProps, "invalid">;
  history?: CopyHistory;
  /** The saved texts by API field (the history hides Restore on equal ones). */
  savedTexts?: Readonly<Record<string, string>>;
}

/** LinkedIn tab of the publish panel. */
export interface LinkedInTabProps {
  text: string;
  onTextChange: (text: string) => void;
  language: ViewerLanguage;
  setLanguage: (language: ViewerLanguage) => void;
  pdfHref: string;
  /** Present when saving is wired: the save bar of the LinkedIn posts. */
  save?: Omit<CopySaveBarProps, "invalid">;
  history?: CopyHistory;
  /** The saved texts by API field (the history hides Restore on equal ones). */
  savedTexts?: Readonly<Record<string, string>>;
}

/** A review-step editor (or its leave guard) over the shared copy editor. */
export interface ReviewCopyEditorProps {
  editor: CopyEditor;
  /** The version history shown under the editor. */
  history?: CopyHistory;
}

/** The version list under one text editor. */
export interface CopyVersionListProps {
  history: CopyHistory | undefined;
  /** The API field names this editor edits (``caption``, ``linkedin_post_pt``…). */
  fields: readonly string[];
  /** The text has unsaved edits: a restore would drop them, so it waits. */
  blocked: boolean;
  /** The saved text per API field: a version equal to it is not restorable. */
  current?: Readonly<Record<string, string>>;
}

/** The version list once there is a history to show. */
export interface CopyVersionEntriesProps extends CopyVersionListProps {
  history: CopyHistory;
  current: Readonly<Record<string, string>>;
}
