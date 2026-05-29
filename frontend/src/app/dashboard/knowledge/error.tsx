"use client";
import { NeonButton } from "@/components/atoms/neon-button";

import { useEffect } from "react";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { Container } from "@/components/layout";
import { AlertCircle } from "lucide-react";

export default function KnowledgeError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  const t = useTranslations("knowledge");
  const tc = useTranslations("common");

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
          <h1 className="text-3xl font-bold">{t("errorTitle")}</h1>
          <p className="text-[var(--color-muted-foreground)] max-w-md">
            {t("errorDescription")}
          </p>
        </div>

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
