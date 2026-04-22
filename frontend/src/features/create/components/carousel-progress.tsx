import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import {
  PIPELINE_PHASES,
  SLIDE_GENERATION_STATUS,
  type SlideGenerationStatus,
  STALLED_THRESHOLD_MS,
} from "@/constants/create";

if (typeof window !== "undefined") {
  console.log("[CarouselProgress] MODULE LOADED in client");
}

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
  /** ISO timestamp of the last backend status update (from /status). */
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
  console.log("[CarouselProgress] rendering", { currentPhase, isComplete, hasError, updatedAt });
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
      <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4">
        <div className="flex items-start gap-2 text-red-500">
          <ErrorIcon />
          <div className="flex-1 space-y-1">
            <span className="font-medium">{t("progress.failed")}</span>
            {errorMessage ? (
              <p className="break-words font-mono text-red-400 text-xs">
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
        <div className="flex items-start gap-2 rounded-md border border-yellow-500/30 bg-yellow-500/10 p-2 text-yellow-400 text-xs">
          <WarningIcon />
          <span>{t("progress.stalled", { seconds: Math.floor(stalledSeconds) })}</span>
        </div>
      ) : null}

      {phaseProgress ? (
        <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3">
          <p className="text-[var(--color-text)] text-sm" data-testid="phase-progress-label">
            {phaseProgress.label}
          </p>
          {phaseProgress.detail ? (
            <p className="text-[var(--color-text-muted)] text-xs italic">
              {phaseProgress.detail}
            </p>
          ) : null}
          {typeof phaseProgress.current === "number" &&
          typeof phaseProgress.total === "number" &&
          phaseProgress.total > 0 ? (
            <div className="space-y-1">
              <div className="flex justify-between text-[var(--color-text-muted)] text-xs tabular-nums">
                <span>{phaseProgress.current} / {phaseProgress.total}</span>
                <span>{Math.round((phaseProgress.current / phaseProgress.total) * 100)}%</span>
              </div>
              <div className="h-1 overflow-hidden rounded-full bg-[var(--color-border)]">
                <div
                  className="h-full bg-[var(--color-primary)] transition-all"
                  style={{
                    width: `${Math.min(100, (phaseProgress.current / phaseProgress.total) * 100)}%`,
                  }}
                  data-testid="phase-progress-bar"
                />
              </div>
            </div>
          ) : null}
          {phaseProgress.slides && phaseProgress.slides.length > 0 ? (
            <ul
              className="space-y-1.5 pt-1"
              aria-label="Per-slide image generation status"
              data-testid="phase-progress-slides"
            >
              {phaseProgress.slides.map((slide) => (
                <li
                  key={slide.number}
                  className="flex items-start gap-2 text-xs"
                  data-testid={`phase-slide-${slide.number}`}
                  data-status={slide.status}
                >
                  <SlideStatusIcon status={slide.status} />
                  <div className="flex-1 space-y-0.5">
                    <span className="font-medium text-[var(--color-text)]">
                      Slide {slide.number}
                    </span>
                    {slide.scene ? (
                      <p className="text-[var(--color-text-muted)] italic">
                        {slide.scene}
                      </p>
                    ) : null}
                  </div>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      <div className="space-y-3">
        {PHASE_ORDER.map((phase, index) => {
          const isActive = index === currentIndex;
          const isPast = index < currentIndex || isComplete;

          return (
            <div
              key={phase}
              className="flex items-center gap-3"
              data-testid={`phase-item-${phase}`}
            >
              <div
                className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold transition-colors ${
                  isPast
                    ? "bg-[var(--color-primary)] text-[var(--color-text)]"
                    : isActive
                      ? "border-2 border-[var(--color-primary)] text-[var(--color-primary)]"
                      : "border border-[var(--color-border)] text-[var(--color-text-muted)]"
                }`}
                aria-current={isActive ? "step" : undefined}
              >
                {isPast ? (
                  <CheckIcon testId="phase-check" />
                ) : isActive ? (
                  <Spinner small />
                ) : (
                  index + 1
                )}
              </div>
              <span
                data-testid={`phase-label-${phase}`}
                className={`text-sm ${
                  isActive
                    ? "font-medium text-[var(--color-primary)]"
                    : isPast
                      ? "text-[var(--color-text)]"
                      : "text-[var(--color-text-muted)]"
                }`}
              >
                {t(`progress.phases.${phase}`)}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function useStalledSeconds(updatedAt: string | undefined, frozen: boolean): number {
  const [seconds, setSeconds] = useState(0);
  useEffect(() => {
    if (!updatedAt || frozen) {
      setSeconds(0);
      return;
    }
    // Backend emits naive ISO timestamps (no Z, no offset) that are
    // actually UTC. JavaScript's Date parser would treat those as local
    // time and produce a wrong diff. Append "Z" when neither suffix is
    // present so the value is always interpreted as UTC.
    const normalized =
      /[zZ]|[+-]\d{2}:?\d{2}$/.test(updatedAt) ? updatedAt : `${updatedAt}Z`;
    const referenceMs = new Date(normalized).getTime();
    const compute = (): void => {
      const since = (Date.now() - referenceMs) / 1000;
      setSeconds(Math.max(0, since));
    };
    compute();
    const id = window.setInterval(compute, 1000);
    return () => window.clearInterval(id);
  }, [updatedAt, frozen]);
  return seconds;
}

function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}

function CheckIcon({ testId }: { testId?: string } = {}): React.ReactElement {
  return (
    <svg
      className="h-4 w-4"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
      data-testid={testId}
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
    </svg>
  );
}

function ErrorIcon(): React.ReactElement {
  return (
    <svg
      className="h-4 w-4 shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v4m0 4h.01M4.93 19h14.14a2 2 0 001.74-3L13.74 4a2 2 0 00-3.48 0L3.19 16a2 2 0 001.74 3z" />
    </svg>
  );
}

function WarningIcon(): React.ReactElement {
  return (
    <svg
      className="h-4 w-4 shrink-0"
      fill="none"
      viewBox="0 0 24 24"
      stroke="currentColor"
      strokeWidth={2}
      aria-hidden="true"
    >
      <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01" />
      <circle cx="12" cy="12" r="9" />
    </svg>
  );
}

const SLIDE_STATUS_ICON: Record<SlideGenerationStatus, () => React.ReactElement> = {
  [SLIDE_GENERATION_STATUS.DONE]: () => (
    <span className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-[var(--color-primary)] text-[10px] text-[var(--color-text)]">
      ✓
    </span>
  ),
  [SLIDE_GENERATION_STATUS.FAILED]: () => (
    <span className="mt-0.5 inline-flex h-4 w-4 shrink-0 items-center justify-center rounded-full bg-red-500 text-[10px] text-white">
      ×
    </span>
  ),
  [SLIDE_GENERATION_STATUS.IN_FLIGHT]: () => <Spinner small />,
  [SLIDE_GENERATION_STATUS.PENDING]: () => (
    <span className="mt-1 inline-flex h-2 w-2 shrink-0 rounded-full border border-[var(--color-border)]" />
  ),
};

function SlideStatusIcon({
  status,
}: {
  status: SlideGenerationStatus;
}): React.ReactElement {
  return SLIDE_STATUS_ICON[status]();
}

function Spinner({ small }: { small?: boolean } = {}): React.ReactElement {
  const size = small ? "h-3 w-3" : "h-4 w-4";
  return (
    <svg
      className={`${size} animate-spin text-[var(--color-primary)]`}
      fill="none"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth={4} />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z" />
    </svg>
  );
}
