import type { EditorialWorkflowState } from "@/modules/publishing";
import { asRecord, resolvePresentationPreviewText } from "@/modules/editorial";

export function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function outlineTitle(
  slide: Record<string, unknown>,
  fallback: string,
): string {
  return asString(slide.title) || asString(slide.heading) || fallback;
}

/** Hook candidates stored on outline slide 1 (POV / Radar IA v4). */
export function outlineHookCandidates(
  slide: Record<string, unknown> | undefined,
): string[] {
  const raw = slide?.hook_candidates;
  return Array.isArray(raw)
    ? raw.filter((item): item is string => typeof item === "string" && !!item)
    : [];
}

/** False when the outline check found no thesis word on slides 1-2. */
export function outlineThesisEarly(
  slide: Record<string, unknown> | undefined,
): boolean {
  const checks = asRecord(slide?.outline_checks);
  return checks.thesis_early !== false;
}

export function draftText(slide: Record<string, unknown>): string {
  const preview = resolvePresentationPreviewText(
    asRecord(slide.presentation_pt),
  );
  if (preview.trim()) {
    return preview;
  }
  return asString(slide.draft_text) || asString(slide.body) || "";
}

function readProgressField(
  state: EditorialWorkflowState,
  key: string,
): unknown {
  return state.phase_progress?.[key];
}

export function resolveBlogMarkdown(state: EditorialWorkflowState): string {
  return (
    state.blog_markdown ?? asString(readProgressField(state, "blog_markdown"))
  );
}

export function resolveRubricScores(
  state: EditorialWorkflowState,
): Record<string, unknown> {
  if (state.rubric_scores && Object.keys(state.rubric_scores).length > 0) {
    return state.rubric_scores;
  }
  const fromProgress = readProgressField(state, "rubric_scores");
  if (fromProgress && typeof fromProgress === "object") {
    return fromProgress as Record<string, unknown>;
  }
  return {};
}
