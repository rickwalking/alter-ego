import { useState } from "react";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type {
  WorkflowPostActionMessages,
  WorkflowPostActionResult,
} from "./types";

export function useWorkflowPostAction(
  messages: WorkflowPostActionMessages,
  onDone?: () => void,
): WorkflowPostActionResult {
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const post = async (url: string, body: object) => {
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await authenticatedFetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!response.ok) {
        throw new Error(messages.failed);
      }
      setMessage(messages.success);
      onDone?.();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : messages.failed);
    } finally {
      setSubmitting(false);
    }
  };

  return { submitting, message, post };
}
