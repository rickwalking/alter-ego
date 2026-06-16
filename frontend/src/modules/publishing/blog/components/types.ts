/**
 * Blog component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

export interface AccessibilityCheckerProps {
  postId: string | null;
}

export interface AiSuggestionPanelProps {
  postId: string;
  selectedText: string;
  onApplySuggestion: (text: string) => void;
  personaId?: string;
}

export interface BlogPostFiltersProps {
  search: string;
  status: string;
  onSearchChange: (value: string) => void;
  onStatusChange: (value: string) => void;
}

export interface ImageGenModalProps {
  postId: string;
  open: boolean;
  onClose: () => void;
  onImageGenerated: (imageUrl: string) => void;
}

export interface KeyboardShortcutsHelpProps {
  open: boolean;
  onClose: () => void;
}

export interface RichTextEditorProps {
  value: string;
  onChange: (value: string) => void;
  onSelectionChange?: (selectedText: string) => void;
  className?: string;
  placeholder?: string;
}

export interface SeoPreviewProps {
  postId: string | null;
  title: string;
  slug: string;
  metaTitle?: string;
  metaDescription?: string;
  excerpt?: string;
  featuredImageUrl?: string | null;
}

export interface BlogPostVersion {
  version_number: number;
  title: string;
  excerpt?: string;
  snapshot?: Record<string, unknown>;
  created_at?: string;
}

export interface VersionHistorySidebarProps {
  postId: string;
  currentBody: string;
  onRestore: (version: BlogPostVersion) => void;
}
