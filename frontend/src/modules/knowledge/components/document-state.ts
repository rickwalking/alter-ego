import { MS_PER_MINUTE } from "@/constants/time";
import type { Document } from "@/schemas/knowledge";

const DOCUMENT_STALE_AFTER_MINUTES = 10;

/** A pending/processing document untouched this long is treated as stuck. */
export const DOCUMENT_STALE_AFTER_MS =
  DOCUMENT_STALE_AFTER_MINUTES * MS_PER_MINUTE;

const IN_FLIGHT_STATUSES: ReadonlySet<string> = new Set([
  "pending",
  "processing",
]);
const FAILED_STATUS = "failed";
const KNOWN_STATUSES: ReadonlySet<string> = new Set([
  ...IN_FLIGHT_STATUSES,
  "completed",
  FAILED_STATUS,
]);

/** Pending or processing, but not updated for longer than the stale window. */
export function isStaleDocument(document: Document, now: number): boolean {
  return (
    IN_FLIGHT_STATUSES.has(document.status) &&
    now - Date.parse(document.updated_at) > DOCUMENT_STALE_AFTER_MS
  );
}

/** Failed or stale: the card explains it and offers a retry. */
export function needsRetry(document: Document, now: number): boolean {
  return document.status === FAILED_STATUS || isStaleDocument(document, now);
}

/** Whether `status` has a translated label under `knowledge.document.status`. */
export function isKnownStatus(status: string): boolean {
  return KNOWN_STATUSES.has(status);
}
