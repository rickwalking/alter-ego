"use client";

import { RouteErrorView } from "@/components/molecules/route-error-view";

export default function ChatError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <RouteErrorView
      error={error}
      reset={reset}
      namespace="chat"
      logLabel="Chat error:"
      showErrorMessage
    />
  );
}
