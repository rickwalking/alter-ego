/**
 * `knowledge` — bounded-context public contract (AE-0139).
 *
 * Owns the knowledge-base surface — document CRUD/upload hooks, document query
 * options, the document card adapter, and the knowledge-base UI components —
 * migrated from the legacy `features/knowledge` folder. This barrel is the ONLY
 * import surface for cross-context and `app/` consumers; everything else under
 * `modules/knowledge/**` is internal.
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

/* --- query options / keys --- */
export {
  documentKeys,
  documentsOptions,
  documentOptions,
} from "./queries";

/* --- hooks --- */
export {
  useDocuments,
  useDocument,
  useCreateDocument,
  useDeleteDocument,
  useReprocessDocument,
} from "./hooks/use-documents";
export { useUploadDocument } from "./hooks/use-upload";

/* --- adapters --- */
export { mapDocumentToCardProps } from "./adapters/document-adapter";

/* --- components --- */
export { KnowledgeBaseInterface } from "./components/knowledge-base-interface";
export { DocumentCard } from "./components/document-card";
export { DocumentList } from "./components/document-list";
export { DocumentForm } from "./components/document-form";
export { FileUpload } from "./components/file-upload";
