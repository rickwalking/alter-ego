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
