/** Document status values. */
export const DOCUMENT_STATUS = {
  PENDING: "pending",
  PROCESSING: "processing",
  COMPLETED: "completed",
  FAILED: "failed",
} as const;

/** Message role values. */
export const MESSAGE_ROLE = {
  USER: "user",
  ASSISTANT: "assistant",
  SYSTEM: "system",
} as const;

/** File type mappings. */
export const FILE_TYPES = {
  PDF: "application/pdf",
  TEXT: "text/plain",
  MARKDOWN: "text/markdown",
} as const;

/** Supported file extensions. */
export const SUPPORTED_EXTENSIONS = [
  ".pdf",
  ".txt",
  ".md",
  ".markdown",
] as const;

/** Upload limits. */
export const UPLOAD_LIMITS = {
  MAX_FILE_SIZE_MB: 50,
  MAX_FILE_SIZE_BYTES: 50 * 1024 * 1024,
} as const;
