/** Editorial carousel workflow hook with SSE updates. */

import { useCallback, useEffect, useState } from "react";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { EDITORIAL_REVIEW_ACTIONS } from "@/constants/blog-ai";
import type { EditorialWorkflowState } from "@/features/blog/types-ai";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface StartWorkflowInput {
  topic: string;
  audience: string;
  brief: string;
  sources: Array<{ title: string; content: string; source_type?: string }>;
  personaId?: string;
}

export function useEditorialWorkflow(projectId: string) {
  const [state, setState] = useState<EditorialWorkflowState | null>(null);
  const [phaseEvents, setPhaseEvents] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (typeof EventSource === "undefined") {
      return;
    }

    const source = new EventSource(
      API_ENDPOINTS.CAROUSEL_WORKFLOW_STREAM(projectId),
      {
        withCredentials: true,
      },
    );

    const handlePhaseChange = (event: MessageEvent<string>): void => {
      try {
        const payload = JSON.parse(event.data) as { phase?: string };
        if (payload.phase) {
          setPhaseEvents((prev) => [...prev, payload.phase as string]);
        }
      } catch {
        // Ignore malformed SSE payloads.
      }
    };

    source.addEventListener("project.phase.changed", handlePhaseChange);
    return () => {
      source.removeEventListener("project.phase.changed", handlePhaseChange);
      source.close();
    };
  }, [projectId]);

  const start = useCallback(
    async (input: StartWorkflowInput): Promise<EditorialWorkflowState> => {
      setLoading(true);
      setError(null);
      try {
        const response = await authenticatedFetch(
          API_ENDPOINTS.CAROUSEL_WORKFLOW_START(projectId),
          {
            method: HTTP_METHODS.POST,
            body: JSON.stringify({
              topic: input.topic,
              audience: input.audience,
              brief: input.brief,
              sources: input.sources,
              persona_id: input.personaId,
            }),
          },
        );
        if (!response.ok) {
          throw new Error("Failed to start editorial workflow");
        }
        const workflowState = (await response.json()) as EditorialWorkflowState;
        setState(workflowState);
        return workflowState;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Workflow start failed";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [projectId],
  );

  const resume = useCallback(
    async (
      action: string,
      feedback?: string,
    ): Promise<EditorialWorkflowState> => {
      setLoading(true);
      setError(null);
      try {
        const response = await authenticatedFetch(
          API_ENDPOINTS.CAROUSEL_WORKFLOW_RESUME(projectId),
          {
            method: HTTP_METHODS.POST,
            body: JSON.stringify({ action, feedback }),
          },
        );
        if (!response.ok) {
          throw new Error("Failed to resume editorial workflow");
        }
        const workflowState = (await response.json()) as EditorialWorkflowState;
        setState(workflowState);
        return workflowState;
      } catch (err) {
        const message =
          err instanceof Error ? err.message : "Workflow resume failed";
        setError(message);
        throw err;
      } finally {
        setLoading(false);
      }
    },
    [projectId],
  );

  return {
    state,
    phaseEvents,
    loading,
    error,
    start,
    resume,
    approve: () => resume(EDITORIAL_REVIEW_ACTIONS.APPROVE),
    reject: (feedback: string) =>
      resume(EDITORIAL_REVIEW_ACTIONS.REJECT, feedback),
  };
}
