import type { FileUploadForm } from "../hooks/types";
/**
 * Knowledge-base component prop types (colocated `types.ts`).
 *
 * Per the component-type-location convention
 * (`frontend/scripts/component-type-location.config.mjs`), component prop shapes
 * live here rather than inline in the `.tsx` files.
 */

import { type Document, type CreateDocumentRequest } from "@/schemas/knowledge";
import type {
  DocumentScopeChoice,
  ScopeFilterValue,
} from "@/constants/knowledge";

export interface DocumentCardProps {
  document: Document;
  onDelete?: () => void;
  /** Reprocess a failed or stuck document. */
  onRetry?: () => void;
  /** A retry of this document is in flight. */
  retrying?: boolean;
  /** The last retry of this document could not be started. */
  retryFailed?: boolean;
  /** Move the document to the given scope. */
  onChangeScope?: (scope: DocumentScopeChoice) => void;
  /** A scope change of this document is in flight. */
  changingScope?: boolean;
  /** The last scope change of this document failed. */
  scopeChangeFailed?: boolean;
}

/** The action row of a document card (everything but delete). */
export type DocumentCardActionsProps = Omit<DocumentCardProps, "onDelete"> & {
  /** Render-time clock (ms) the stale check compares against. */
  now: number;
};

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
  /** Move a document to the given scope. */
  onChangeScope?: (id: string, scope: DocumentScopeChoice) => void;
  /** Ids of the documents whose scope change is in flight. */
  changingScopeIds?: ReadonlySet<string>;
  /** Ids of the documents whose last scope change failed. */
  scopeChangeFailedIds?: ReadonlySet<string>;
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
  onChangeScope: (id: string, scope: DocumentScopeChoice) => void;
  changingScopeIds: ReadonlySet<string>;
  scopeChangeFailedIds: ReadonlySet<string>;
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

/** Title + tags + scope inputs for the upload. */
export interface UploadMetadataFieldsProps {
  title: string;
  onTitleChange: (value: string) => void;
  tags: string;
  onTagsChange: (value: string) => void;
  scope: DocumentScopeChoice;
  onScopeChange: (value: DocumentScopeChoice) => void;
  disabled: boolean;
}

/** A document's scope badge. */
export interface ScopeBadgeProps {
  scope: string;
}

/** The personal / public choice of a form. */
export interface ScopeFieldProps {
  value: DocumentScopeChoice;
  onChange: (value: DocumentScopeChoice) => void;
  disabled?: boolean;
}

/** The scope filter of the document list. */
export interface ScopeFilterProps {
  value: ScopeFilterValue;
  onChange: (value: ScopeFilterValue) => void;
}

/** The scope switch of a document card. */
export interface ScopeSwitchProps {
  scope: DocumentScopeChoice;
  onSwitch: () => void;
  changing: boolean;
  failed: boolean;
}

/** The upload drop target. */
export interface DropZoneProps {
  form: FileUploadForm;
  typeValid: boolean;
}
