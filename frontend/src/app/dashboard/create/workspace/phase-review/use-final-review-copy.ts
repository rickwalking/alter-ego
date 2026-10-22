"use client";

import { useCarouselProject } from "@/modules/editorial";
import {
  mergePublishProjectWithWorkflow,
  useCopyEditor,
  useCopySave,
  type CopySource,
  type EditorialWorkflowState,
} from "@/modules/publishing";

type CopyEditor = ReturnType<typeof useCopyEditor>;

/** The final review's caption / LinkedIn editor and how its project load went. */
export interface FinalReviewCopy {
  /** Null until the saved project texts are loaded. */
  editor: CopyEditor | null;
  /** The project could not be loaded; ``retry`` asks again. */
  loadFailed: boolean;
  retry: () => void;
}

const NO_TEXTS: CopySource = {
  caption: null,
  linkedin_post_pt: null,
  linkedin_post_en: null,
};

/**
 * The caption and LinkedIn posts the final review edits: the saved project
 * texts first, the workflow checkpoint's only where the project has none (the
 * publish page's rule, so both pages show the same text). A save sends the
 * workflow lock version and refetches the workflow state and the project, so
 * the approve that follows sends the new lock version. No editor is offered
 * until the project loads (a failed load can be retried).
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
  const editor = useCopyEditor(
    project ? mergePublishProjectWithWorkflow(project, state) : NO_TEXTS,
    saveCopy,
  );
  return {
    editor: project ? editor : null,
    loadFailed: !project && projectQuery.isError,
    retry: () => {
      void refetchProject();
    },
  };
}
