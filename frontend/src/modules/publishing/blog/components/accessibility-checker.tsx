"use client";

import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  NeonCard,
  NeonCardContent,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { useAccessibilityCheck } from "@/modules/publishing/blog/hooks/use-accessibility-check";

interface AccessibilityCheckerProps {
  postId: string | null;
}

export function AccessibilityChecker({ postId }: AccessibilityCheckerProps) {
  const t = useTranslations("blogEditorial.accessibility");
  const { result, loading, error, check } = useAccessibilityCheck(postId);

  return (
    <NeonCard>
      <NeonCardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <NeonCardTitle className="text-sm">{t("title")}</NeonCardTitle>
          {postId && (
            <NeonButton
              size="sm"
              variant="outline"
              onClick={() => void check()}
              disabled={loading}
            >
              {loading ? t("checking") : t("runCheck")}
            </NeonButton>
          )}
        </div>
      </NeonCardHeader>
      <NeonCardContent className="space-y-2">
        {error && (
          <NeonAlert variant="destructive">
            <NeonAlertDescription>{error}</NeonAlertDescription>
          </NeonAlert>
        )}
        {result && (
          <>
            <NeonBadge variant={result.passed ? "default" : "destructive"}>
              {t("score", { score: result.overall_score })}
            </NeonBadge>
            {result.issues.length === 0 && (
              <p className="text-sm text-green-700">{t("noIssues")}</p>
            )}
            {result.issues.map((issue) => (
              <NeonAlert
                key={issue.code}
                variant={issue.severity === "error" ? "destructive" : "default"}
              >
                <NeonAlertDescription>{issue.message}</NeonAlertDescription>
              </NeonAlert>
            ))}
          </>
        )}
        {!result && !loading && (
          <p className="text-xs text-muted-foreground">{t("hint")}</p>
        )}
      </NeonCardContent>
    </NeonCard>
  );
}
