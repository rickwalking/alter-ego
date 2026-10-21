/**
 * Blog component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import type { BlogEditorError } from "../types";

export interface AiSuggestionPanelProps {
  postId: string;
  selectedText: string;
  onApplySuggestion: (text: string) => void;
  personaId?: string;
}

export interface BlogPostVersion {
  version_number: number;
  /** Absent on entries written before the section editor (restore-only history). */
  title?: string | null;
  excerpt?: string | null;
  snapshot?: Record<string, unknown>;
  change_summary?: string | null;
  created_at?: string;
}

export interface EditorErrorNoticeProps {
  /** The failed action's error; `null` renders nothing. */
  error: BlogEditorError | null;
}

export interface VersionHistorySidebarProps {
  versions: BlogPostVersion[];
  loading: boolean;
  /** The editor's current text, shown next to the selected snapshot. */
  currentText: string;
  /** Pending edits block a restore (it would replace them). */
  disabled: boolean;
  /** Restores the version; resolves with the failure or `null` on success. */
  onRestore: (versionNumber: number) => Promise<BlogEditorError | null>;
}
