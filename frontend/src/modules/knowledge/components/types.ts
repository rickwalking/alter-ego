import type { FileUploadForm } from "../hooks/types";
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

/** The dropped/picked file shown in the drop zone (AE-0446). */
export interface SelectedFileSummaryProps {
  file: File;
  pending: boolean;
  typeValid: boolean;
  onRemove: () => void;
}

/** Title + tags inputs for the upload (AE-0446). */
export interface UploadMetadataFieldsProps {
  title: string;
  onTitleChange: (value: string) => void;
  tags: string;
  onTagsChange: (value: string) => void;
  disabled: boolean;
}

/** The upload drop target (AE-0446). */
export interface DropZoneProps {
  form: FileUploadForm;
  typeValid: boolean;
}
