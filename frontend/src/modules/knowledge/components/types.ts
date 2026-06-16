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
  isLoading?: boolean;
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
