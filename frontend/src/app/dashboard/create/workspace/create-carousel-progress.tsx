"use client";

import { useTranslations } from "next-intl";
import {
  PIPELINE_PHASES,
  type SlideGenerationStatus,
  STALLED_THRESHOLD_MS,
} from "@/constants/create";

import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";

import { PhaseItem } from "./phase-item";
import { PhaseProgressDetail } from "./phase-progress-detail";

import { WorkflowStatusBadge } from "./workflow-status-badge";

import {
  CompleteCard,
  ErrorCard,
  StalledWarning,
  useStalledSeconds,
  formatElapsed,
} from "./create-carousel-progress-parts";

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

function ProgressHeader({
  phaseLabel,
  stalledSeconds,
}: Readonly<{
  phaseLabel: string;
  stalledSeconds: number;
}>) {
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

function ActiveProgress({
  currentPhase,
  isComplete,
  stalledSeconds,
  phaseProgress,
}: Readonly<{
  currentPhase: string;
  isComplete: boolean;
  stalledSeconds: number;
  phaseProgress?: PhaseProgress | null;
}>) {
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
}: Readonly<CarouselProgressProps>) {
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
