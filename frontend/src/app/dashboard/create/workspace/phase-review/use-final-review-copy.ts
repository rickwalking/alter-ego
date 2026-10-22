"use client";

import { useCarouselProject } from "@/modules/editorial";
import {
  mergePublishProjectWithWorkflow,
  useCopyEditor,
  useCopySave,
  type CopySource,
  type EditorialWorkflowState,
} from "@/modules/publishing";
import type { CarouselProjectResponse } from "@/schemas/carousel";

type CopyEditor = ReturnType<typeof useCopyEditor>;

/** The final review's caption / LinkedIn editor, once the project loaded. */
export interface FinalReviewCopy {
  project: CarouselProjectResponse | undefined;
  editor: CopyEditor | null;
}

/** The saved project texts, falling back to the checkpoint's per text. */
function copySource(
  project: CarouselProjectResponse | undefined,
  state: EditorialWorkflowState,
): CopySource {
  if (project) {
    return mergePublishProjectWithWorkflow(project, state);
  }
  return {
    caption: state.caption ?? null,
    linkedin_post_pt: state.linkedin_post_pt ?? null,
    linkedin_post_en: state.linkedin_post_en ?? null,
  };
}

/**
 * The caption and LinkedIn posts the final review edits: the saved project
 * texts first, the workflow checkpoint's only where the project has none (the
 * publish page's rule, so both pages show the same text). A save sends the
 * workflow lock version and refetches the workflow state and the project, so
 * the approve that follows sends the new lock version.
 */
export function useFinalReviewCopy(
  projectId: string,
  state: EditorialWorkflowState,
  onCopySaved: () => Promise<unknown>,
): FinalReviewCopy {
  const projectQuery = useCarouselProject(projectId);
  const project = projectQuery.data;
  const refetchProject = projectQuery.refetch;
  const saveCopy = useCopySave(projectId, state.lock_version, () =>
    Promise.all([onCopySaved(), refetchProject()]),
  );
  const editor = useCopyEditor(copySource(project, state), saveCopy);
  return { project, editor: project ? editor : null };
}
