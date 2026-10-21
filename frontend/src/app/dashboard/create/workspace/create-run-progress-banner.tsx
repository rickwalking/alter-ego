"use client";

/**
 * Live "revision in progress" banner for the create flow.
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
import { EDITORIAL_REVIEW_ACTIONS } from "@/constants/blog-ai";
import {
  nextEditorialPhase,
  usePhaseLabel,
} from "@/app/dashboard/create/workspace/editorial-phase-labels";

const ELAPSED_TICK_MS = 1_000;
const KNOWN_STAGES: readonly string[] = Object.values(EDITORIAL_RUN_STAGES);

export interface CreateRunProgressBannerProps {
  currentPhase: string;
  runStartedAt?: string | null;
  runStage?: string | null;
  /**
   * The review action that started the run ("approve" runs the
   * NEXT phase, "revise" re-runs the current one); null after a reload.
   */
  runningAction?: string | null;
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

interface BannerCopy {
  titleKey: string;
  phaseKey: string;
  phase: string;
}

/** Name the phase that is really running. */
function bannerCopy(
  currentPhase: string,
  runningAction: string | null | undefined,
): BannerCopy {
  if (runningAction === EDITORIAL_REVIEW_ACTIONS.APPROVE) {
    return {
      titleKey: "titleApprove",
      phaseKey: "phaseNext",
      phase: nextEditorialPhase(currentPhase),
    };
  }
  if (runningAction === EDITORIAL_REVIEW_ACTIONS.REVISE) {
    return {
      titleKey: "title",
      phaseKey: "phaseRevising",
      phase: currentPhase,
    };
  }
  return {
    titleKey: "titleRunning",
    phaseKey: "phaseAfter",
    phase: currentPhase,
  };
}

function formatClock(date: Date): string {
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  return `${hours}:${minutes}`;
}

interface Elapsed {
  ms: number;
  minutes: number;
  seconds: number;
}

function elapsedSince(startedAtMs: number, now: number): Elapsed {
  const ms = Math.max(0, now - startedAtMs);
  return {
    ms,
    minutes: Math.floor(ms / 60_000),
    seconds: Math.floor((ms % 60_000) / 1_000),
  };
}

/** Offer "check again" once the run has been going for a while. */
function checkAgainDue(elapsed: Elapsed | null): boolean {
  return elapsed !== null && elapsed.ms >= EDITORIAL_RUN_CHECK_AGAIN_AFTER_MS;
}

/** Live elapsed time since the run started (a UI timer, not data fetching). */
function useElapsed(startedAtMs: number | null): Elapsed | null {
  const [now, setNow] = useState<number>(() => Date.now());
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
  return startedAtMs === null ? null : elapsedSince(startedAtMs, now);
}

export function CreateRunProgressBanner({
  currentPhase,
  runStartedAt,
  runStage,
  runningAction,
  onCheckAgain,
  checkAgainDisabled = false,
}: Readonly<CreateRunProgressBannerProps>): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.runProgress");
  const phaseLabel = usePhaseLabel();
  const copy = bannerCopy(currentPhase, runningAction);
  const startedAt = parseStartedAt(runStartedAt);
  const elapsed = useElapsed(startedAt?.getTime() ?? null);
  const showCheckAgain = checkAgainDue(elapsed);
  const stageLabel =
    runStage && KNOWN_STAGES.includes(runStage) ? t(`stage.${runStage}`) : null;

  return (
    <NeonAlert role="status" data-testid="run-progress-banner">
      <NeonAlertTitle>{t(copy.titleKey)}</NeonAlertTitle>
      <NeonAlertDescription>
        <div className="space-y-1">
          <p>
            {t(copy.phaseKey, { phase: phaseLabel(copy.phase) })}
            {stageLabel ? ` — ${stageLabel}` : null}
          </p>
          {startedAt && elapsed !== null && (
            <p>
              {t("startedAt", { time: formatClock(startedAt) })}{" "}
              {t("elapsed", {
                minutes: elapsed.minutes,
                seconds: elapsed.seconds,
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
