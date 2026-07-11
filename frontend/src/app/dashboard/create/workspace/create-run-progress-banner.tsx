"use client";

/**
 * AE-0315: live "revision in progress" banner for the create flow.
 *
 * Rendered on EVERY step while `phase_status === in_progress`: shows the
 * running phase, the coarse stage, when the run started, and a live elapsed
 * timer. Past the stale threshold it offers "Check again" (a state refetch —
 * the backend reaper clears genuinely dead runs), so the UI is never
 * permanently disabled. Reconstructs entirely from workflow state
 * (`run_started_at`/`run_stage`), with no dependency on having witnessed the
 * `run.started` SSE event.
 */

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
  NeonAlertTitle,
} from "@/components/molecules/neon-alert";
import { NeonButton } from "@/components/atoms/neon-button";
import {
  EDITORIAL_RUN_CHECK_AGAIN_AFTER_MS,
  EDITORIAL_RUN_STAGES,
} from "@/constants/editorial-workflow";

const ELAPSED_TICK_MS = 1_000;
const KNOWN_STAGES: readonly string[] = Object.values(EDITORIAL_RUN_STAGES);

export interface CreateRunProgressBannerProps {
  currentPhase: string;
  runStartedAt?: string | null;
  runStage?: string | null;
  onCheckAgain: () => void;
  checkAgainDisabled?: boolean;
}

function parseStartedAt(runStartedAt: string | null | undefined): Date | null {
  if (!runStartedAt) {
    return null;
  }
  const parsed = new Date(runStartedAt);
  return Number.isNaN(parsed.getTime()) ? null : parsed;
}

function formatClock(date: Date): string {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

export function CreateRunProgressBanner({
  currentPhase,
  runStartedAt,
  runStage,
  onCheckAgain,
  checkAgainDisabled = false,
}: CreateRunProgressBannerProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.runProgress");
  const startedAt = parseStartedAt(runStartedAt);
  const startedAtMs = startedAt?.getTime() ?? null;
  const [now, setNow] = useState<number>(() => Date.now());

  // Live elapsed ticker — a UI timer, not data fetching.
  useEffect(() => {
    if (startedAtMs === null) {
      return;
    }
    const interval = window.setInterval(() => {
      setNow(Date.now());
    }, ELAPSED_TICK_MS);
    return () => {
      window.clearInterval(interval);
    };
  }, [startedAtMs]);

  const elapsedMs =
    startedAtMs !== null ? Math.max(0, now - startedAtMs) : null;
  const elapsedMinutes =
    elapsedMs !== null ? Math.floor(elapsedMs / 60_000) : null;
  const elapsedSeconds =
    elapsedMs !== null ? Math.floor((elapsedMs % 60_000) / 1_000) : null;
  const showCheckAgain =
    elapsedMs !== null && elapsedMs >= EDITORIAL_RUN_CHECK_AGAIN_AFTER_MS;
  const stageLabel =
    runStage && KNOWN_STAGES.includes(runStage) ? t(`stage.${runStage}`) : null;

  return (
    <NeonAlert role="status" data-testid="run-progress-banner">
      <NeonAlertTitle>{t("title")}</NeonAlertTitle>
      <NeonAlertDescription>
        <div className="space-y-1">
          <p>
            {t("phase", { phase: currentPhase })}
            {stageLabel ? ` — ${stageLabel}` : null}
          </p>
          {startedAt && elapsedMinutes !== null && elapsedSeconds !== null && (
            <p>
              {t("startedAt", { time: formatClock(startedAt) })}{" "}
              {t("elapsed", {
                minutes: elapsedMinutes,
                seconds: elapsedSeconds,
              })}
            </p>
          )}
          <p>{t("actionsDisabled")}</p>
          {showCheckAgain && (
            <div className="pt-1">
              <p className="pb-1">{t("stillRunningHint")}</p>
              <NeonButton
                type="button"
                variant="outline"
                size="sm"
                onClick={onCheckAgain}
                disabled={checkAgainDisabled}
              >
                {t("checkAgain")}
              </NeonButton>
            </div>
          )}
        </div>
      </NeonAlertDescription>
    </NeonAlert>
  );
}
