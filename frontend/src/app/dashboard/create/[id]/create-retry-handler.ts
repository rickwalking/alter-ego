import type { EditorialWorkflowState } from "@/features/blog/types-ai";

type WorkflowSource = {
  title: string;
  content: string;
  source_type?: string;
};

type StartWorkflow = (input: {
  topic: string;
  audience: string;
  brief: string;
  sources: WorkflowSource[];
}) => Promise<EditorialWorkflowState | null>;

export interface RetryWorkflowHandlerDeps {
  /** Project inputs; nullish when the project has not loaded yet. */
  project: { topic: string; audience: string; niche: string } | null | undefined;
  /** Current in-flight guard value (true while a retry is running). */
  retrying: boolean;
  /** Toggles the in-flight guard / button disabled state. */
  setRetrying: (value: boolean) => void;
  /** Workflow start action (rejects on failure). */
  start: StartWorkflow;
  /** Sources to replay on retry. */
  sources: WorkflowSource[];
  /** Navigates to the next step on success. */
  navigateOnSuccess: () => void;
}

/**
 * Build the editorial-workflow retry handler (AE-0009).
 *
 * Extracted from the create workspace page so the retry branches are unit
 * testable without a full page harness:
 *  - Guard: no-op when the project is missing or a retry is already in flight.
 *  - Success: ``start()`` resolves -> reset ``retrying`` and navigate.
 *  - Failure: ``start()`` rejects -> reset ``retrying`` (button re-enables) and
 *    stay on the failed view (no navigation), keeping the error card visible.
 */
export function createRetryWorkflowHandler(
  deps: RetryWorkflowHandlerDeps,
): () => Promise<void> {
  return async (): Promise<void> => {
    const { project, retrying, setRetrying, start, sources, navigateOnSuccess } =
      deps;
    if (!project || retrying) return;
    setRetrying(true);
    try {
      await start({
        topic: project.topic,
        audience: project.audience,
        brief: project.niche,
        sources,
      });
      setRetrying(false);
      navigateOnSuccess();
    } catch {
      setRetrying(false);
    }
  };
}
