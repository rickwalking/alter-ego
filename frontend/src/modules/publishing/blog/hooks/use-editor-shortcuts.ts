"use client";

import { useEffect } from "react";
import {
  SHORTCUT_AI_SUGGEST,
  SHORTCUT_HELP,
  SHORTCUT_SAVE,
  SHORTCUT_SUBMIT_REVIEW,
} from "@/constants/editor-shortcuts";
import type { EditorShortcutHandlers } from "./types";

const SHORTCUT_MATCHERS: Record<string, (event: KeyboardEvent) => boolean> = {
  [SHORTCUT_SAVE]: (event) => event.key.toLowerCase() === "s",
  [SHORTCUT_SUBMIT_REVIEW]: (event) =>
    event.shiftKey && event.key.toLowerCase() === "r",
  [SHORTCUT_AI_SUGGEST]: (event) =>
    event.shiftKey && event.key.toLowerCase() === "a",
  [SHORTCUT_HELP]: (event) => event.key === "/",
};

function matchShortcut(event: KeyboardEvent, combo: string): boolean {
  const mod = event.metaKey || event.ctrlKey;
  if (!mod) return false;
  const matcher = SHORTCUT_MATCHERS[combo] as
    | ((event: KeyboardEvent) => boolean)
    | undefined;
  return matcher ? matcher(event) : false;
}

export function useEditorShortcuts(
  handlers: EditorShortcutHandlers,
  enabled = true,
) {
  useEffect(() => {
    if (!enabled) return;

    const shortcutHandlers: Array<[string, (() => void) | undefined]> = [
      [SHORTCUT_SAVE, handlers.onSave],
      [SHORTCUT_SUBMIT_REVIEW, handlers.onSubmitReview],
      [SHORTCUT_AI_SUGGEST, handlers.onAiSuggest],
      [SHORTCUT_HELP, handlers.onShowHelp],
    ];

    const onKeyDown = (event: KeyboardEvent) => {
      for (const [combo, handler] of shortcutHandlers) {
        if (matchShortcut(event, combo) && handler) {
          event.preventDefault();
          handler();
          return;
        }
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handlers, enabled]);
}
