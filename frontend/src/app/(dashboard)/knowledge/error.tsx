"use client";

import { useEffect } from "react";
import Link from "next/link";
import { Container } from "@/components/layout";
import { Button } from "@/components/ui/button";
import { AlertCircle } from "lucide-react";

export default function KnowledgeError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("Knowledge base error:", error);
  }, [error]);

  return (
    <Container className="py-20">
      <div className="flex flex-col items-center text-center space-y-6">
        <div className="h-20 w-20 rounded-full bg-[var(--color-destructive)]/10 flex items-center justify-center">
          <AlertCircle className="h-10 w-10 text-[var(--color-destructive)]" />
        </div>

        <div className="space-y-2">
          <h1 className="text-3xl font-bold">Failed to load Knowledge Base</h1>
          <p className="text-[var(--color-muted-foreground)] max-w-md">
            We could not load your documents. This might be a temporary issue.
          </p>
        </div>

        <div className="flex gap-4">
          <Button onClick={reset}>Try Again</Button>
          <Link href="/">
            <Button variant="outline">Go Home</Button>
          </Link>
        </div>
      </div>
    </Container>
  );
}
