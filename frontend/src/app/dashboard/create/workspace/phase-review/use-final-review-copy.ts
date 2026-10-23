"use client";

import { useEffect } from "react";
import { useCarouselProject } from "@/modules/editorial";
import {
  COPY_FIELDS,
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

/** A caption / LinkedIn edit is unsaved, or a save is still running. */
export function copyBusy(copy: FinalReviewCopy): boolean {
  const editor = copy.editor;
  if (!editor) {
    return false;
  }
  return editor.isDirty(COPY_FIELDS) || editor.status.kind === "saving";
}

/**
 * Tell the workflow panel whether the review's texts are busy (unsaved or
 * saving), so approve and send back wait; leaving the step reports idle.
 */
export function useReportCopyBusy(
  copy: FinalReviewCopy,
  onCopyBusyChange: ((busy: boolean) => void) | undefined,
): void {
  const busy = copyBusy(copy);
  useEffect(() => {
    onCopyBusyChange?.(busy);
  }, [busy, onCopyBusyChange]);
  useEffect(
    () => () => {
      onCopyBusyChange?.(false);
    },
    [onCopyBusyChange],
  );
}
