"use client";

import { useTranslations } from "next-intl";
import { Alert, AlertDescription, Badge, Button } from "@/components/ui";
import { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";

interface EditorialWorkflowPanelProps {
  projectId: string;
  topic: string;
  audience: string;
  brief: string;
}

export function EditorialWorkflowPanel({
  projectId,
  topic,
  audience,
  brief,
}: EditorialWorkflowPanelProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  const { state, phaseEvents, loading, error, start, approve, reject, awaitingHumanReview } =
    useEditorialWorkflow(projectId);

  return (
    <div className="space-y-4 rounded-lg border p-4">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold">{t("title")}</h3>
        <Button
          size="sm"
          disabled={loading}
          onClick={() =>
            void start({
              topic,
              audience,
              brief,
              sources: [],
            })
          }
        >
          {t("actions.start")}
        </Button>
      </div>

      {error && (
        <Alert variant="destructive">
          <AlertDescription>{error}</AlertDescription>
        </Alert>
      )}

      {state && (
        <div className="space-y-2 text-sm">
          <p>
            {t("currentPhase")}:{" "}
            <Badge variant="secondary">{state.current_phase}</Badge>
          </p>
          <p>
            {t("phaseStatus")}: <Badge>{state.phase_status}</Badge>
          </p>
          <div className="flex gap-2">
            <Button
              size="sm"
              disabled={loading || !awaitingHumanReview}
              onClick={() => void approve()}
            >
              {t("actions.approve")}
            </Button>
            <Button
              size="sm"
              variant="outline"
              disabled={loading || !awaitingHumanReview}
              onClick={() => void reject("Needs revision")}
            >
              {t("actions.reject")}
            </Button>
          </div>
        </div>
      )}

      {phaseEvents.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {phaseEvents.map((phase) => (
            <Badge key={phase} variant="outline">
              {phase}
            </Badge>
          ))}
        </div>
      )}
    </div>
  );
}
