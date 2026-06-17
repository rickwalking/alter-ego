"use client";

import { useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { AlertCircle } from "lucide-react";

import { NeonButton } from "@/components/atoms/neon-button";
import { Container } from "@/components/layout";

export interface RouteErrorViewProps {
  error: Error & { digest?: string };
  reset: () => void;
  /** next-intl namespace holding errorTitle / errorDescription / tryAgain. */
  namespace: string;
  /** console.error prefix for this route's boundary. */
  logLabel: string;
  /** When true, render the raw error message block (defaults to false). */
  showErrorMessage?: boolean;
}

/**
 * Shared Next.js route error boundary view (AE-0154). The dashboard `error.tsx`
 * boundaries differ only by translation namespace, log label, and whether the
 * raw error message is shown — so they delegate to this component.
 */
export function RouteErrorView({
  error,
  reset,
  namespace,
  logLabel,
  showErrorMessage = false,
}: RouteErrorViewProps): React.ReactElement {
  const t = useTranslations(namespace);
  const tc = useTranslations("common");

  useEffect(() => {
    console.error(logLabel, error);
  }, [error, logLabel]);

  return (
    <Container className="py-20">
      <div className="flex flex-col items-center text-center space-y-6">
        <div className="h-20 w-20 rounded-full bg-[var(--color-destructive)]/10 flex items-center justify-center">
          <AlertCircle className="h-10 w-10 text-[var(--color-destructive)]" />
        </div>

        <div className="space-y-2">
          <h1 className="text-3xl font-bold">{t("errorTitle")}</h1>
          <p className="text-[var(--color-muted-foreground)] max-w-md">
            {t("errorDescription")}
          </p>
        </div>

        {showErrorMessage && error.message && (
          <div className="bg-[var(--color-muted)] p-4 rounded-lg max-w-lg">
            <p className="text-sm font-mono text-[var(--color-destructive)]">
              {error.message}
            </p>
          </div>
        )}

        <div className="flex gap-4">
          <NeonButton onClick={reset}>{t("tryAgain")}</NeonButton>
          <Link href="/">
            <NeonButton variant="outline">{tc("goHome")}</NeonButton>
          </Link>
        </div>
      </div>
    </Container>
  );
}
