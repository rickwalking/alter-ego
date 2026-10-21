/** Knowledge upload file checks. */

const ALLOWED_UPLOAD_TYPES = [
  "application/pdf",
  "text/plain",
  "text/markdown",
  "text/x-markdown",
];
const ALLOWED_UPLOAD_EXTENSION = /\.(pdf|txt|md|markdown)$/i;

const BYTES_PER_KB = 1024;
const BYTES_PER_MB = BYTES_PER_KB * BYTES_PER_KB;

export function formatFileSize(bytes: number): string {
  if (bytes < BYTES_PER_KB) return `${bytes} B`;
  if (bytes < BYTES_PER_MB) return `${(bytes / BYTES_PER_KB).toFixed(1)} KB`;
  return `${(bytes / BYTES_PER_MB).toFixed(1)} MB`;
}

/** PDF, text or markdown, by MIME type or (as browsers vary) by extension. */
export function isAllowedUploadFile(file: File | null): boolean {
  if (!file) {
    return true;
  }
  return (
    ALLOWED_UPLOAD_TYPES.includes(file.type) ||
    ALLOWED_UPLOAD_EXTENSION.test(file.name)
  );
}
