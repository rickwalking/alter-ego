/** Keyboard shortcut definitions for blog editor (UI-030). */

export const SHORTCUT_SAVE = "mod+s";
export const SHORTCUT_SUBMIT_REVIEW = "mod+shift+r";
export const SHORTCUT_AI_SUGGEST = "mod+shift+a";
export const SHORTCUT_HELP = "mod+/";

export const EDITOR_SHORTCUTS = [
  { keys: "Ctrl+S", action: "save" },
  { keys: "Ctrl+Shift+R", action: "submitReview" },
  { keys: "Ctrl+Shift+A", action: "aiSuggest" },
  { keys: "Ctrl+/", action: "showHelp" },
] as const;
