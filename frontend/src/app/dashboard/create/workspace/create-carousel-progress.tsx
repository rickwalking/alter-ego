"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  PIPELINE_PHASES,
  type SlideGenerationStatus,
  STALLED_THRESHOLD_MS,
} from "@/constants/create";
import { NEON_AMBER, NEON_AMBER_DIM } from "@/constants/neon";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { PhaseItem } from "./phase-item";
import { PhaseProgressDetail } from "./phase-progress-detail";
import { ErrorIcon, WarningIcon } from "./progress-icons";
import { WorkflowStatusBadge } from "./workflow-status-badge";
import { WORKFLOW_STATUS_COMPLETED } from "./workflow-status";

interface PhaseProgressSlide {
  number: number;
  status: SlideGenerationStatus;
  style?: string;
  scene?: string;
}

interface PhaseProgress {
  phase: string;
  label: string;
  current?: number;
  total?: number;
  detail?: string;
  slides?: PhaseProgressSlide[];
}

interface CarouselProgressProps {
  currentPhase: string;
  isComplete: boolean;
  hasError: boolean;
  /** ISO timestamp of the last backend status update (from /status or /stream). */
  updatedAt?: string;
  /** Backend-reported failure message (when `hasError`). */
  errorMessage?: string | null;
  /** Backend-reported fine-grained progress (label + optional current/total). */
  phaseProgress?: PhaseProgress | null;
}

const PHASE_ORDER = PIPELINE_PHASES as readonly string[];

function resolvePipelinePhaseLabel(
  currentPhase: string,
  translate: ReturnType<typeof useTranslations>,
): string {
  if (!currentPhase || !PHASE_ORDER.includes(currentPhase)) {
    return translate("progress.phases.pending");
  }
  return translate(`progress.phases.${currentPhase}`);
}

function CompleteCard() {
  const t = useTranslations("create");
  return (
    <div className="rounded-lg border border-neon-card-border bg-bg-card p-4">
      <div className="flex items-center gap-2">
        <WorkflowStatusBadge status={WORKFLOW_STATUS_COMPLETED} />
        <span className="font-medium text-text-primary">
          {t("progress.complete")}
        </span>
      </div>
    </div>
  );
}

function ErrorCard({ errorMessage }: { errorMessage?: string | null }) {
  const t = useTranslations("create");
  return (
    <NeonAlert variant="destructive">
      <div className="flex items-start gap-2">
        <ErrorIcon />
        <div className="flex-1 space-y-1">
          <span className="font-medium">{t("progress.failed")}</span>
          {errorMessage ? (
            <NeonAlertDescription className="break-words font-mono text-xs">
              {errorMessage}
            </NeonAlertDescription>
          ) : null}
        </div>
      </div>
    </NeonAlert>
  );
}

function ProgressHeader({
  phaseLabel,
  stalledSeconds,
}: {
  phaseLabel: string;
  stalledSeconds: number;
}) {
  const t = useTranslations("create");
  return (
    <div className="flex items-start justify-between gap-3 border-b border-neon-card-border pb-3">
      <div className="flex flex-col gap-1">
        <span className="text-text-muted text-xs uppercase tracking-wide">
          {t("progress.currentlyProcessing")}
        </span>
        <div className="flex flex-wrap items-center gap-2">
          <WorkflowStatusBadge status={WORKFLOW_PHASE_STATUS.IN_PROGRESS} />
          <span className="font-medium text-sm text-text-primary">
            {phaseLabel}
          </span>
        </div>
      </div>
      <span className="text-text-muted text-xs tabular-nums">
        {formatElapsed(stalledSeconds)}
      </span>
    </div>
  );
}

function StalledWarning({ stalledSeconds }: { stalledSeconds: number }) {
  const t = useTranslations("create");
  return (
    <div
      className="flex items-start gap-2 rounded-md p-2 text-xs"
      style={{ background: NEON_AMBER_DIM, color: NEON_AMBER }}
    >
      <WarningIcon />
      <span>
        {t("progress.stalled", { seconds: Math.floor(stalledSeconds) })}
      </span>
    </div>
  );
}

function ActiveProgress({
  currentPhase,
  isComplete,
  stalledSeconds,
  phaseProgress,
}: {
  currentPhase: string;
  isComplete: boolean;
  stalledSeconds: number;
  phaseProgress?: PhaseProgress | null;
}) {
  const t = useTranslations("create");
  const currentIndex = PHASE_ORDER.indexOf(
    currentPhase && PHASE_ORDER.includes(currentPhase) ? currentPhase : "",
  );
  const isStalled = stalledSeconds >= STALLED_THRESHOLD_MS / 1000;
  const phaseLabel = resolvePipelinePhaseLabel(currentPhase, t);

  return (
    <div className="space-y-3 rounded-lg border border-neon-card-border bg-bg-card p-4">
      <ProgressHeader phaseLabel={phaseLabel} stalledSeconds={stalledSeconds} />

      {isStalled ? <StalledWarning stalledSeconds={stalledSeconds} /> : null}

      {phaseProgress ? (
        <PhaseProgressDetail
          label={phaseProgress.label}
          detail={phaseProgress.detail}
          current={phaseProgress.current}
          total={phaseProgress.total}
          slides={phaseProgress.slides}
        />
      ) : null}

      <div className="space-y-3">
        {PHASE_ORDER.map((phase, index) => (
          <PhaseItem
            key={phase}
            phase={phase}
            isActive={index === currentIndex}
            isPast={index < currentIndex || isComplete}
            index={index}
          />
        ))}
      </div>
    </div>
  );
}

export function CarouselProgress({
  currentPhase,
  isComplete,
  hasError,
  updatedAt,
  errorMessage,
  phaseProgress,
}: CarouselProgressProps) {
  const stalledSeconds = useStalledSeconds(updatedAt, isComplete || hasError);

  if (isComplete) return <CompleteCard />;
  if (hasError) return <ErrorCard errorMessage={errorMessage} />;

  return (
    <ActiveProgress
      currentPhase={currentPhase}
      isComplete={isComplete}
      stalledSeconds={stalledSeconds}
      phaseProgress={phaseProgress}
    />
  );
}

/**
 * Seconds since the last backend update. Frozen when the pipeline
 * terminates. Backend emits naive ISO timestamps that are actually UTC;
 * we append "Z" when no offset is present so `new Date(...)` treats
 * them as UTC instead of local time.
 */
function useStalledSeconds(
  updatedAt: string | undefined,
  frozen: boolean,
): number {
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!updatedAt || frozen) {
      return;
    }
    const id = window.setInterval(() => setTick((tick) => tick + 1), 1000);
    return () => window.clearInterval(id);
  }, [updatedAt, frozen]);

  if (!updatedAt || frozen) {
    return 0;
  }

  return secondsSince(updatedAt);
}

function secondsSince(updatedAt: string): number {
  const normalized = /[zZ]|[+-]\d{2}:?\d{2}$/.test(updatedAt)
    ? updatedAt
    : `${updatedAt}Z`;
  const referenceMs = new Date(normalized).getTime();
  return Math.max(0, (Date.now() - referenceMs) / 1000);
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}
