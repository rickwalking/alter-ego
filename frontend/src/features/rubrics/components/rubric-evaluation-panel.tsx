"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonAlert, NeonAlertDescription } from "@/components/molecules/neon-alert";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { CONTENT_TYPE_BLOG_POST } from "@/constants/rubrics";
import type { RubricEvaluationResult } from "@/features/blog/types-ai";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

interface RubricEvaluationPanelProps {
  rubricId: string;
}

export function RubricEvaluationPanel({
  rubricId,
}: RubricEvaluationPanelProps): React.JSX.Element {
  const t = useTranslations("rubrics");
  const [content, setContent] = useState("");
  const [result, setResult] = useState<RubricEvaluationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const evaluate = async (): Promise<void> => {
    setLoading(true);
    setError(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.RUBRIC_EVALUATE(rubricId),
        {
          method: HTTP_METHODS.POST,
          body: JSON.stringify({
            content_type: CONTENT_TYPE_BLOG_POST,
            content_text: content,
            sources: [],
          }),
        },
      );
      if (!response.ok) {
        throw new Error("Evaluation failed");
      }
      setResult((await response.json()) as RubricEvaluationResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Evaluation failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-3 rounded-lg border p-4 mt-4">
      <h4 className="font-medium">{t("evaluation.title")}</h4>
      <NeonTextarea
        value={content}
        onChange={(event) => setContent(event.target.value)}
        rows={4}
      />
      <NeonButton
        disabled={loading || !content.trim()}
        onClick={() => void evaluate()}
      >
        {t("evaluation.run")}
      </NeonButton>
      {error && (
        <NeonAlert variant="destructive">
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      )}
      {result && (
        <div className="space-y-2">
          <NeonBadge variant={result.passed ? "default" : "destructive"}>
            {t("evaluation.score", { score: Math.round(result.overall_score) })}{" "}
            — {result.passed ? t("evaluation.passed") : t("evaluation.failed")}
          </NeonBadge>
          <ul className="text-sm space-y-1">
            {Object.entries(result.scores).map(([criterionId, score]) => (
              <li key={criterionId}>
                {criterionId}: {score.score} (
                {score.passed ? t("evaluation.pass") : t("evaluation.fail")})
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
