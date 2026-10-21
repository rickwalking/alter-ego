/** Input of the document upload mutation (AE-0446: moved out of the hook). */
export interface UploadDocumentInput {
  file: File;
  title?: string;
  tags?: string;
  onProgress?: (progress: number) => void;
}
