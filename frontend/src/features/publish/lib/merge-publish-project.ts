import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import type { CarouselProjectResponse } from "@/schemas/carousel";

/** Prefer persisted project fields; fall back to workflow checkpoint copy. */
export function mergePublishProjectWithWorkflow(
  project: CarouselProjectResponse,
  workflow: EditorialWorkflowState | null | undefined,
): CarouselProjectResponse {
  if (!workflow) {
    return project;
  }
  return {
    ...project,
    caption: project.caption ?? workflow.caption ?? null,
    linkedin_post_pt:
      project.linkedin_post_pt ?? workflow.linkedin_post_pt ?? null,
    linkedin_post_en:
      project.linkedin_post_en ?? workflow.linkedin_post_en ?? null,
  };
}
