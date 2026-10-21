import type { UseMutationResult } from "@tanstack/react-query";
import type { DocumentUploadResponse } from "@/schemas/knowledge";
/** Input of the document upload mutation (AE-0446: moved out of the hook). */
export interface UploadDocumentInput {
  file: File;
  title?: string;
  tags?: string;
  onProgress?: (progress: number) => void;
}

/** State + handlers of the knowledge upload form (AE-0446). */
export interface FileUploadForm {
  isDragging: boolean;
  selectedFile: File | null;
  title: string;
  setTitle: (value: string) => void;
  tags: string;
  setTags: (value: string) => void;
  progress: number;
  clearFile: () => void;
  dropZone: {
    onDragOver: (e: React.DragEvent) => void;
    onDragLeave: (e: React.DragEvent) => void;
    onDrop: (e: React.DragEvent) => void;
  };
  onFileInput: (e: React.ChangeEvent<HTMLInputElement>) => void;
  submit: (onDone?: () => void) => void;
  upload: UseMutationResult<DocumentUploadResponse, Error, UploadDocumentInput>;
}

/** The file-selection half of the upload form (AE-0446). */
export type FilePick = Pick<
  FileUploadForm,
  "isDragging" | "selectedFile" | "dropZone" | "onFileInput"
> & { setSelectedFile: (file: File | null) => void };
