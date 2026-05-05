import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  PIPELINE_PHASES,
  type SlideGenerationStatus,
  STALLED_THRESHOLD_MS,
} from "@/constants/create";
import { PhaseItem } from "./phase-item";
import { PhaseProgressDetail } from "./phase-progress-detail";
import { CheckIcon, ErrorIcon, Spinner, WarningIcon } from "./progress-icons";

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

export function CarouselProgress({
  currentPhase,
  isComplete,
  hasError,
  updatedAt,
  errorMessage,
  phaseProgress,
}: CarouselProgressProps) {
  const t = useTranslations("create");
  const stalledSeconds = useStalledSeconds(updatedAt, isComplete || hasError);

  if (isComplete) {
    return (
      <div className="rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] p-4">
        <div className="flex items-center gap-2 text-[var(--color-primary)]">
          <CheckIcon />
          <span className="font-medium">{t("progress.complete")}</span>
        </div>
      </div>
    );
  }

  if (hasError) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/10 p-4">
        <div className="flex items-start gap-2 text-destructive">
          <ErrorIcon />
          <div className="flex-1 space-y-1">
            <span className="font-medium">{t("progress.failed")}</span>
            {errorMessage ? (
              <p className="break-words font-mono text-destructive/80 text-xs">
                {errorMessage}
              </p>
            ) : null}
          </div>
        </div>
      </div>
    );
  }

  const currentIndex = PHASE_ORDER.indexOf(currentPhase);
  const isStalled = stalledSeconds >= STALLED_THRESHOLD_MS / 1000;

  return (
    <div className="space-y-3 rounded-lg border border-[var(--color-border)] bg-[var(--color-background)] p-4">
      <div className="flex items-start justify-between gap-3 border-b border-[var(--color-border)] pb-3">
        <div className="flex items-center gap-2">
          <Spinner />
          <div className="flex flex-col">
            <span className="text-[var(--color-text-muted)] text-xs uppercase tracking-wide">
              {t("progress.currentlyProcessing")}
            </span>
            <span className="font-medium text-[var(--color-primary)] text-sm">
              {t(`progress.phases.${currentPhase}`)}
            </span>
          </div>
        </div>
        <span className="text-[var(--color-text-muted)] text-xs tabular-nums">
          {formatElapsed(stalledSeconds)}
        </span>
      </div>

      {isStalled ? (
        <div className="flex items-start gap-2 rounded-md border border-warning/30 bg-warning/10 p-2 text-warning-foreground text-xs">
          <WarningIcon />
          <span>
            {t("progress.stalled", { seconds: Math.floor(stalledSeconds) })}
          </span>
        </div>
      ) : null}

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
