/**
 * Knowledge-base component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention (AE-0144,
 * `frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import { type Document, type CreateDocumentRequest } from "@/schemas/knowledge";

export interface DocumentCardProps {
  document: Document;
  onDelete?: () => void;
}

export interface DocumentListProps {
  documents: Document[];
  onCreateNew: () => void;
  onUploadNew: () => void;
  onDeleteDocument: (id: string) => void;
}

/**
 * Props for the Suspense-bound list section (ADR-010). It owns the document
 * read internally (via `useDocuments`), so callers pass only the action
 * handlers — no `documents`/`isLoading` are threaded through.
 */
export interface DocumentListSectionProps {
  onCreateNew: () => void;
  onUploadNew: () => void;
  onDeleteDocument: (id: string) => void;
}

export interface DocumentFormProps {
  onSubmit: (data: CreateDocumentRequest) => void;
  onCancel: () => void;
}

export interface FileUploadProps {
  onUploadComplete?: () => void;
  onCancel?: () => void;
}
