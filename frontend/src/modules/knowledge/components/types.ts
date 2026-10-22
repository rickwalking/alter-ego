import type { FileUploadForm } from "../hooks/types";
/**
 * Knowledge-base component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import { type Document, type CreateDocumentRequest } from "@/schemas/knowledge";

export interface DocumentCardProps {
  document: Document;
  onDelete?: () => void;
  /** Reprocess a failed or stuck document. */
  onRetry?: () => void;
  /** A retry of this document is in flight. */
  retrying?: boolean;
  /** The last retry of this document could not be started. */
  retryFailed?: boolean;
}

export interface DocumentStateRowProps {
  document: Document;
  /** Render-time clock (ms) the stale check compares against. */
  now: number;
  badgeClassName: string;
}

export interface DocumentRetryButtonProps {
  onRetry: () => void;
  retrying: boolean;
  retryFailed: boolean;
}

export interface DocumentListProps {
  documents: Document[];
  onCreateNew: () => void;
  onUploadNew: () => void;
  onDeleteDocument: (id: string) => void;
  onRetryDocument?: (id: string) => void;
  /** Ids of the documents whose retry is in flight. */
  retryingIds?: ReadonlySet<string>;
  /** Ids of the documents whose last retry failed. */
  retryFailedIds?: ReadonlySet<string>;
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
  onRetryDocument: (id: string) => void;
  retryingIds: ReadonlySet<string>;
  retryFailedIds: ReadonlySet<string>;
}

export interface DocumentFormProps {
  onSubmit: (data: CreateDocumentRequest) => void;
  onCancel: () => void;
}

export interface FileUploadProps {
  onUploadComplete?: () => void;
  onCancel?: () => void;
}

/** The dropped/picked file shown in the drop zone. */
export interface SelectedFileSummaryProps {
  file: File;
  pending: boolean;
  typeValid: boolean;
  onRemove: () => void;
}

/** Title + tags inputs for the upload. */
export interface UploadMetadataFieldsProps {
  title: string;
  onTitleChange: (value: string) => void;
  tags: string;
  onTagsChange: (value: string) => void;
  disabled: boolean;
}

/** The upload drop target. */
export interface DropZoneProps {
  form: FileUploadForm;
  typeValid: boolean;
}
