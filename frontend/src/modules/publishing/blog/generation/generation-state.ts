/**
 * Read the generation run state out of a post's `ai_generation_metadata`.
 * The metadata is a free-form JSON object, so every field is
 * narrowed here and anything unexpected reads as "no run".
 */

import {
  GENERATION_METADATA_KEY,
  GENERATION_STATUS,
  type GenerationStatus,
} from "./generation-constants";

export interface GenerationError {
  code: string;
  slot?: string;
  reason?: string;
}

export interface GenerationState {
  status: GenerationStatus;
  attempt: number;
  warnings: string[];
  errors: GenerationError[];
  recoverable: boolean;
  /** Cover + one per section (N + 1); 0 on rows written before generation runs recorded it. */
  imageSlots: number;
  imageCount: number;
}

const KNOWN_STATUSES = new Set<string>(Object.values(GENERATION_STATUS));

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function count(value: unknown): number {
  return typeof value === "number" && value >= 0 ? value : 0;
}

function strings(value: unknown): string[] {
  return Array.isArray(value)
    ? value.filter((item): item is string => typeof item === "string")
    : [];
}

function toError(value: unknown): GenerationError | null {
  if (!isRecord(value) || typeof value.code !== "string") {
    return null;
  }
  return {
    code: value.code,
    slot: typeof value.slot === "string" ? value.slot : undefined,
    reason: typeof value.reason === "string" ? value.reason : undefined,
  };
}

function errors(value: unknown): GenerationError[] {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map(toError)
    .filter((item): item is GenerationError => item !== null);
}

/** The run state, or `null` when the post was never generated. */
export function readGenerationState(
  metadata: Record<string, unknown> | null | undefined,
): GenerationState | null {
  const generation = metadata?.[GENERATION_METADATA_KEY];
  if (!isRecord(generation) || typeof generation.status !== "string") {
    return null;
  }
  if (!KNOWN_STATUSES.has(generation.status)) {
    return null;
  }
  return {
    status: generation.status as GenerationStatus,
    attempt: typeof generation.attempt === "number" ? generation.attempt : 1,
    warnings: strings(generation.warnings),
    errors: errors(generation.errors),
    recoverable: generation.recoverable === true,
    imageSlots: count(generation.image_slots),
    imageCount: count(generation.image_count),
  };
}

/** True while the post's generation run is writing it (editor read-only). */
export function isGenerationInProgress(
  post:
    | { ai_generation_metadata?: Record<string, unknown> | null }
    | null
    | undefined,
): boolean {
  return (
    readGenerationState(post?.ai_generation_metadata)?.status ===
    GENERATION_STATUS.IN_PROGRESS
  );
}
