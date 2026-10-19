"use client";

/**
 * Server-side actions of the blog section editor (AE-0424, ADR-0025).
 *
 * Slot actions (generate/regenerate an image, rewrite a section in the
 * persona voice, generate the EN translation) save pending edits first, then
 * call the route with `If-Match` and merge only that slot's answer into the
 * draft. Each slot tracks its own pending/error state so a failure shows a
 * visible retry on that slot while the rest stays editable.
 *
 * Review actions (submit / approve / reject / publish / unpublish / schedule
 * / cancel) call the existing workflow routes and take the answer wholesale.
 */

import { useState } from "react";

import { BLOG_EDITOR_ERROR_KINDS } from "@/constants/blog-editor";
import {
  BlogEditorRequestError,
  generateEnTranslation,
  generateSlotImage,
  rewriteSection,
} from "../blog-editor-requests";
import {
  withServerBody,
  withServerImage,
  withServerTranslation,
  type BlogImageSlotRef,
} from "../lib/editor-document";
import type {
  BlogEditorError,
  BlogEditorSlotActions,
  SlotRun,
  SlotStatus,
  UseBlogPostEditorResult,
} from "./types";

const COVER_KEY = "cover";
const REWRITE_SUFFIX = "rewrite";
const TRANSLATION_KEY = "translation:en";
const IDLE: SlotStatus = { pending: false, error: null };

export function imageSlotKey(slot: BlogImageSlotRef): string {
  return `${slot.language}:${slot.sectionId ?? COVER_KEY}`;
}

export function rewriteSlotKey(slot: {
  language: string;
  sectionId: string;
}): string {
  return `${slot.language}:${slot.sectionId}:${REWRITE_SUFFIX}`;
}

export const TRANSLATION_SLOT_KEY = TRANSLATION_KEY;

function toError(err: unknown): BlogEditorError {
  if (err instanceof BlogEditorRequestError) {
    return { kind: err.kind, detail: err.detail };
  }
  return { kind: BLOG_EDITOR_ERROR_KINDS.FAILED, detail: null };
}

export function useBlogEditorActions(
  editor: UseBlogPostEditorResult,
  personaId: string | null,
): BlogEditorSlotActions {
  const [status, setStatus] = useState<Record<string, SlotStatus>>({});
  const mark = (key: string, next: SlotStatus): void =>
    setStatus((prev) => ({ ...prev, [key]: next }));

  const run = async ({ key, task, merge }: SlotRun): Promise<void> => {
    mark(key, { pending: true, error: null });
    const target = await editor.ensureSaved();
    if (!target) {
      mark(key, IDLE);
      return;
    }
    try {
      editor.applyServerPost(await task(target), merge);
      mark(key, IDLE);
    } catch (err) {
      const error = toError(err);
      mark(key, { pending: false, error });
      if (error.kind === BLOG_EDITOR_ERROR_KINDS.MIGRATION_PENDING) {
        editor.setError(error);
      }
    }
  };

  const generateImage = (
    slot: BlogImageSlotRef,
    prompt: string | null,
  ): Promise<void> =>
    run({
      key: imageSlotKey(slot),
      task: (target) => generateSlotImage(target, { slot, prompt }),
      merge: (draft, server) => withServerImage(draft, server, slot),
    });

  const rewrite = (sectionId: string): Promise<void> => {
    const slot = { language: editor.language, sectionId };
    return run({
      key: rewriteSlotKey(slot),
      task: (target) => rewriteSection(target, { ...slot, personaId }),
      merge: (draft, server) => withServerBody(draft, server, slot),
    });
  };

  const generateTranslation = (): Promise<void> =>
    run({
      key: TRANSLATION_KEY,
      task: (target) => generateEnTranslation(target),
      merge: (draft, server) => withServerTranslation(draft, server),
    });

  return {
    statusOf: (key: string) => status[key] ?? IDLE,
    anyPending: Object.values(status).some((slot) => slot.pending),
    generateImage,
    rewrite,
    generateTranslation,
  };
}
