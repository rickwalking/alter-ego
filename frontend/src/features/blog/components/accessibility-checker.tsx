"use client";

import { useTranslations } from "next-intl";
import {
  Alert,
  AlertDescription,
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui";
import { useAccessibilityCheck } from "@/features/blog/hooks/use-accessibility-check";

interface AccessibilityCheckerProps {
  postId: string | null;
}

export function AccessibilityChecker({ postId }: AccessibilityCheckerProps) {
  const t = useTranslations("blogEditorial.accessibility");
  const { result, loading, error, check } = useAccessibilityCheck(postId);

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">{t("title")}</CardTitle>
          {postId && (
            <Button
              size="sm"
              variant="outline"
              onClick={() => void check()}
              disabled={loading}
            >
              {loading ? t("checking") : t("runCheck")}
            </Button>
          )}
        </div>
      </CardHeader>
      <CardContent className="space-y-2">
        {error && (
          <Alert variant="destructive">
            <AlertDescription>{error}</AlertDescription>
          </Alert>
        )}
        {result && (
          <>
            <Badge variant={result.passed ? "default" : "destructive"}>
              {t("score", { score: result.overall_score })}
            </Badge>
            {result.issues.length === 0 && (
              <p className="text-sm text-green-700">{t("noIssues")}</p>
            )}
            {result.issues.map((issue) => (
              <Alert
                key={issue.code}
                variant={issue.severity === "error" ? "destructive" : "default"}
              >
                <AlertDescription>{issue.message}</AlertDescription>
              </Alert>
            ))}
          </>
        )}
        {!result && !loading && (
          <p className="text-xs text-muted-foreground">{t("hint")}</p>
        )}
      </CardContent>
    </Card>
  );
}
