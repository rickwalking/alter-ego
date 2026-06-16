"use client";

import { useEffect } from "react";
import {
  SHORTCUT_AI_SUGGEST,
  SHORTCUT_HELP,
  SHORTCUT_SAVE,
  SHORTCUT_SUBMIT_REVIEW,
} from "@/constants/editor-shortcuts";

interface EditorShortcutHandlers {
  onSave?: () => void;
  onSubmitReview?: () => void;
  onAiSuggest?: () => void;
  onShowHelp?: () => void;
}

function matchShortcut(event: KeyboardEvent, combo: string): boolean {
  const mod = event.metaKey || event.ctrlKey;
  if (combo === SHORTCUT_SAVE) return mod && event.key.toLowerCase() === "s";
  if (combo === SHORTCUT_SUBMIT_REVIEW)
    return mod && event.shiftKey && event.key.toLowerCase() === "r";
  if (combo === SHORTCUT_AI_SUGGEST)
    return mod && event.shiftKey && event.key.toLowerCase() === "a";
  if (combo === SHORTCUT_HELP) return mod && event.key === "/";
  return false;
}

export function useEditorShortcuts(
  handlers: EditorShortcutHandlers,
  enabled = true,
) {
  useEffect(() => {
    if (!enabled) return;

    const onKeyDown = (event: KeyboardEvent) => {
      if (matchShortcut(event, SHORTCUT_SAVE) && handlers.onSave) {
        event.preventDefault();
        handlers.onSave();
      } else if (
        matchShortcut(event, SHORTCUT_SUBMIT_REVIEW) &&
        handlers.onSubmitReview
      ) {
        event.preventDefault();
        handlers.onSubmitReview();
      } else if (
        matchShortcut(event, SHORTCUT_AI_SUGGEST) &&
        handlers.onAiSuggest
      ) {
        event.preventDefault();
        handlers.onAiSuggest();
      } else if (matchShortcut(event, SHORTCUT_HELP) && handlers.onShowHelp) {
        event.preventDefault();
        handlers.onShowHelp();
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handlers, enabled]);
}
