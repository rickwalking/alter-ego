"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";

import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/publishing";
import {
  isWarningViolation,
  listPresentationViolations,
  resolveLocalizedSlides,
} from "@/modules/editorial";
import {
  ViolationList,
  RecoveryEditSection,
  RecoverySendBackSection,
} from "./design-recovery-sections";

/** AE-0310: recovery callbacks wired from the workflow panel. */
export interface DesignRecoveryActions {
  onSubmitEditedSlides: (slides: LocalizedSlideReview[]) => void;
  onSendBackToContent: (feedback: string) => void;
  disabled?: boolean;
}

interface DesignRecoveryPanelProps {
  state: EditorialWorkflowState;
  recovery?: DesignRecoveryActions;
}

type RecoveryMode = "idle" | "edit" | "sendBack";

function flaggedSlideIndexes(
  violations: SlideValidationViolation[],
): Set<number> {
  const indexes = new Set<number>();
  for (const violation of violations) {
    if (typeof violation.slide_index === "number") {
      indexes.add(violation.slide_index);
    }
  }
  return indexes;
}

export function DesignRecoveryPanel({
  state,
  recovery,
}: DesignRecoveryPanelProps): React.ReactElement {
  const tRecovery = useTranslations("editorialWorkflow.review.designRecovery");
  const t = useTranslations("editorialWorkflow.review");
  const violations = listPresentationViolations(state);
  const baselineSlides = resolveLocalizedSlides(state);
  const [mode, setMode] = useState<RecoveryMode>("idle");
  const flagged = flaggedSlideIndexes(violations);
  const actionsDisabled = recovery?.disabled === true;
  const closeSection = (): void => {
    setMode("idle");
  };

  return (
    <div className="space-y-3">
      <NeonAlert variant="destructive">
        <NeonAlertDescription>
          <span className="block font-medium">{tRecovery("blockedTitle")}</span>
          <span className="block">{tRecovery("hint")}</span>
        </NeonAlertDescription>
      </NeonAlert>

      {violations.length > 0 ? (
        <div className="space-y-2 rounded-md border border-destructive/30 bg-destructive/5 p-3">
          <p className="font-medium text-destructive text-xs">
            {t("violationsTitle")}
          </p>
          <ViolationList
            violations={violations}
            onSelect={() => {
              setMode("edit");
            }}
            selectHint={tRecovery("violationHint")}
            slideLabel={(index) => t("slideLabel", { index })}
            severityLabel={(violation) =>
              isWarningViolation(violation)
                ? t("violationSeverityWarning")
                : t("violationSeverityBlocker")
            }
          />
        </div>
      ) : null}

      {recovery ? (
        <div className="flex flex-wrap gap-2">
          <NeonButton
            size="sm"
            disabled={actionsDisabled}
            onClick={() => {
              setMode("edit");
            }}
          >
            {tRecovery("editAction")}
          </NeonButton>
          <NeonButton
            size="sm"
            disabled={actionsDisabled}
            onClick={() => {
              setMode("sendBack");
            }}
          >
            {tRecovery("sendBackAction")}
          </NeonButton>
        </div>
      ) : null}

      {recovery && mode === "edit" ? (
        <RecoveryEditSection
          baselineSlides={baselineSlides}
          flagged={flagged}
          disabled={actionsDisabled}
          onSubmit={(slides) => {
            recovery.onSubmitEditedSlides(slides);
            closeSection();
          }}
          onCancel={closeSection}
        />
      ) : null}

      {recovery && mode === "sendBack" ? (
        <RecoverySendBackSection
          disabled={actionsDisabled}
          onSubmit={(feedback) => {
            recovery.onSendBackToContent(feedback);
            closeSection();
          }}
          onCancel={closeSection}
        />
      ) : null}
    </div>
  );
}
