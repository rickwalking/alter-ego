"use client";

import { useState } from "react";
import type { CarouselProjectResponse } from "@/schemas/carousel";
import {
  copySaveErrorKey,
  dirtyFields,
  rebaseDrafts,
  savedCopyTexts,
  toCopyPayload,
} from "@/modules/publishing/distribution/lib/copy-editor-state";
import type {
  CopyEditor,
  CopyEditorState,
  CopyField,
  CopyTextsState,
  SaveCopy,
  SaveDirtyFieldsInput,
} from "./types";

const IDLE: CopyEditorState["status"] = { kind: "idle" };

function sameTexts(a: CopyTextsState, b: CopyTextsState): boolean {
  return dirtyFields(a, b).length === 0;
}

/** Send the dirty ``fields`` and mark them saved, or record why it failed. */
async function saveDirtyFields({
  state,
  setState,
  onSaveCopy,
  fields,
}: SaveDirtyFieldsInput): Promise<void> {
  const toSave = dirtyFields(state.draft, state.saved, fields);
  if (!onSaveCopy || toSave.length === 0) {
    return;
  }
  const sent = state.draft;
  setState((current) => ({ ...current, status: { kind: "saving" } }));
  try {
    await onSaveCopy(toCopyPayload(sent, toSave));
    setState((current) => {
      const saved = { ...current.saved };
      for (const field of toSave) {
        saved[field] = sent[field];
      }
      return { ...current, saved, status: { kind: "saved" } };
    });
  } catch (error) {
    setState((current) => ({
      ...current,
      status: { kind: "error", errorKey: copySaveErrorKey(error) },
    }));
  }
}

/**
 * Draft and saved copies of the caption and LinkedIn posts. A project whose
 * texts changed since the last render moves the saved texts and keeps the
 * drafts the owner has not saved (a save marks its texts saved at once, so
 * the page refetch that follows changes nothing on screen);
 * ``save`` sends the dirty fields among those asked and marks them saved.
 */
export function useCopyEditor(
  project: CarouselProjectResponse,
  onSaveCopy: SaveCopy | undefined,
): CopyEditor {
  const incoming = savedCopyTexts(project);
  const [state, setState] = useState<CopyEditorState>({
    seen: incoming,
    saved: incoming,
    draft: incoming,
    status: IDLE,
  });
  if (!sameTexts(state.seen, incoming)) {
    setState({
      seen: incoming,
      saved: incoming,
      draft: rebaseDrafts(state.draft, state.saved, incoming),
      status: state.status,
    });
  }

  const setText = (field: CopyField, text: string): void =>
    setState((current) => ({
      ...current,
      draft: { ...current.draft, [field]: text },
    }));

  const save = (fields: readonly CopyField[]): Promise<void> =>
    saveDirtyFields({ state, setState, onSaveCopy, fields });

  return {
    draft: state.draft,
    status: state.status,
    canSave: onSaveCopy !== undefined,
    isDirty: (fields) =>
      dirtyFields(state.draft, state.saved, fields).length > 0,
    setText,
    save,
  };
}
