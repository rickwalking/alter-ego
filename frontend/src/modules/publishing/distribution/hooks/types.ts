import type { Dispatch, SetStateAction } from "react";
import type { ChatStream } from "@/lib/use-chat-stream";
/**
 * Distribution hook return/payload types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), hook object shapes
 * live here rather than inline in the `use-*.ts` files.
 */

import type { Message } from "@/schemas/chat";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import type { CoverGenerations as CoverGenerationsView } from "./cover-generation-schema";

export interface UsePublishChatReturn {
  conversationId: string | null;
  messages: Message[];
  isStreaming: boolean;
  sendMessage: (content: string) => void;
}

export interface InstagramPublishPayload {
  projectId: string;
  caption: string;
}

/** One editable text of the publish page. */
export type CopyField = "caption" | "linkedinPt" | "linkedinEn";

/** Where the editor reads the saved texts from (a project, or its merge). */
export type CopySource = Pick<
  CarouselProjectResponse,
  "caption" | "linkedin_post_pt" | "linkedin_post_en"
>;

/** The three editable texts, as the editor holds them. */
export type CopyTextsState = Readonly<Record<CopyField, string>>;

/** The caption / LinkedIn texts one save sends (snake_case API fields). */
export interface CarouselCopyTexts {
  caption?: string;
  linkedin_post_pt?: string;
  linkedin_post_en?: string;
}

/** One caption / LinkedIn save at the loaded lock version. */
export interface CarouselCopySaveInput {
  projectId: string;
  lockVersion: number;
  texts: CarouselCopyTexts;
}

/** Saves the given texts; rejects with the API error when refused. */
export type SaveCopy = (texts: CarouselCopyTexts) => Promise<void>;

/** Where the caption / LinkedIn save stands. */
export type CopySaveStatus =
  | { kind: "idle" }
  | { kind: "saving" }
  | { kind: "saved" }
  | { kind: "error"; errorKey: string };

/** The publish-page editor of the caption and the LinkedIn posts. */
export interface CopyEditorState {
  /** The project's texts as last rendered (a change means a refetch). */
  seen: CopyTextsState;
  saved: CopyTextsState;
  draft: CopyTextsState;
  status: CopySaveStatus;
}

/** One save of the copy editor: its state, setter, save call and fields. */
export interface SaveDirtyFieldsInput {
  state: CopyEditorState;
  setState: Dispatch<SetStateAction<CopyEditorState>>;
  onSaveCopy: SaveCopy | undefined;
  fields: readonly CopyField[];
}

/** What ``useCopyEditor`` hands the publish panel. */
export interface CopyEditor {
  draft: CopyTextsState;
  /** The texts as last saved (what the history compares against). */
  saved: CopyTextsState;
  status: CopySaveStatus;
  /** False when the page wired no save (read-only preview). */
  canSave: boolean;
  isDirty: (fields: readonly CopyField[]) => boolean;
  setText: (field: CopyField, text: string) => void;
  save: (fields: readonly CopyField[]) => Promise<void>;
}

/** What ``useLeaveGuard`` hands the page: the open dialog and its answers. */
export interface LeaveGuard {
  asking: boolean;
  stay: () => void;
  leave: () => Promise<void>;
}

/** One slide-1 cover pick at the workflow lock version read. */
export interface CoverPickInput {
  projectId: string;
  assetId: string;
}

/** ``useState`` pair holding the publish chat's conversation id. */
export type ConversationIdState = [
  string | null,
  Dispatch<SetStateAction<string | null>>,
];

/** The stream callbacks one publish-chat turn drives. */
export type PublishTurnCallbacks = Pick<
  ChatStream,
  "appendToken" | "setIsStreaming" | "resetStreamingRefs"
>;

/** What sending one publish-chat turn needs. */
export interface SendPublishDeps {
  projectId: string;
  conversationId: string | null;
  isStreaming: boolean;
  stream: ChatStream;
}

/** One stored version of the caption or a LinkedIn post (API field names). */
export interface CopyVersionView {
  version_number: number;
  field: string;
  text: string;
  author_id: string | null;
  author_name: string | null;
  created_at: string;
  restored_from?: number | null;
}

/** One restore of a stored version at the loaded lock version. */
export interface CopyVersionRestoreInput {
  projectId: string;
  lockVersion: number;
  versionNumber: number;
}

/** Where a restore stands. */
export type CopyRestoreStatus =
  | { kind: "idle" }
  | { kind: "restoring"; versionNumber: number }
  | { kind: "error"; errorKey: string };

/** The history of the caption and LinkedIn posts, and its restore. */
export interface CopyHistory {
  versions: readonly CopyVersionView[];
  loading: boolean;
  status: CopyRestoreStatus;
  /** Absent when the page has no lock version to send. */
  restore?: (versionNumber: number) => Promise<void>;
  /** Older versions exist beyond the loaded pages; ``loadMore`` fetches them. */
  hasMore: boolean;
  loadMore: () => void;
}

/** Upload a file from the device into the owner's photo library; its asset id. */
export type UploadLibraryPhoto = (file: File) => Promise<string>;

/** "Enviar foto": whether the page offers it, its progress and failure. */
export interface CoverPhotoUpload {
  available: boolean;
  uploading: boolean;
  failed: boolean;
  onFile: (file: File) => Promise<void>;
}

/** The photos to send (none for a cover from the prompt alone) and the owner's direction. */
export interface CoverGenerationInput {
  projectId: string;
  photoIds: readonly string[];
  prompt: string;
}

/** Why a new generation is not allowed now (a cap), or null. */
export type CapReason =
  | "carouselCap"
  | "monthlyCap"
  | "carouselAttempts"
  | "monthlyAttempts"
  | null;

/** The "Gerar capa com Grok" form state and actions. */
export interface CoverGenerateForm {
  data: CoverGenerationsView | undefined;
  loadError: Error | null;
  latest: CoverGenerationsView["generations"][number] | null;
  running: boolean;
  blocked: CapReason;
  canGenerate: boolean;
  selected: readonly string[];
  toggle: (assetId: string) => void;
  /** Tick a newly uploaded photo, unless three are already ticked. */
  add: (assetId: string) => void;
  prompt: string;
  setPrompt: (prompt: string) => void;
  asking: CoverGenerationInput | null;
  cancel: () => void;
  ask: () => void;
  confirm: (describe: (code: string | null) => string) => Promise<void>;
}

/** What decides whether "Gerar capa" is enabled. */
export interface GenerateGate {
  loaded: boolean;
  formReady: boolean;
  running: boolean;
  blocked: CapReason;
}
