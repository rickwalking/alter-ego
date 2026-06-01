import type { EditorialWorkflowState } from "@/features/blog/types-ai";

export function asString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

export function outlineTitle(
  slide: Record<string, unknown>,
  fallback: string,
): string {
  return asString(slide.title) || asString(slide.heading) || fallback;
}

export function draftText(slide: Record<string, unknown>): string {
  return asString(slide.draft_text) || asString(slide.body) || "";
}

function readProgressField(
  state: EditorialWorkflowState,
  key: string,
): unknown {
  return state.phase_progress?.[key];
}

export function resolveCaption(state: EditorialWorkflowState): string {
  return state.caption ?? asString(readProgressField(state, "caption"));
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
