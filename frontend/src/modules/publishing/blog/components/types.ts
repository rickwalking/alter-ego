/**
 * Blog component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

export interface AiSuggestionPanelProps {
  postId: string;
  selectedText: string;
  onApplySuggestion: (text: string) => void;
  personaId?: string;
}

export interface BlogPostVersion {
  version_number: number;
  /** Absent on entries written before AE-0424 (restore-only history). */
  title?: string | null;
  excerpt?: string | null;
  snapshot?: Record<string, unknown>;
  change_summary?: string | null;
  created_at?: string;
}

export interface VersionHistorySidebarProps {
  versions: BlogPostVersion[];
  loading: boolean;
  /** The editor's current text, shown next to the selected snapshot. */
  currentText: string;
  /** Pending edits block a restore (it would replace them). */
  disabled: boolean;
  onRestore: (versionNumber: number) => void;
}
