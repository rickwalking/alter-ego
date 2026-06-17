"use client";

import { RouteErrorView } from "@/components/molecules/route-error-view";

export default function KnowledgeError({
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
      namespace="knowledge"
      logLabel="Knowledge base error:"
    />
  );
}
