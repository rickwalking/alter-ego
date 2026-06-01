import {
  SlideProgressGrid,
  type SlideProgressItem,
} from "./slide-progress-grid";

interface PhaseProgressDetailProps {
  /** Backend-provided label (e.g. "Drafting bilingual slide content"). */
  label: string;
  /** Optional extra detail shown italicized under the label. */
  detail?: string;
  /** Numerator for a progress bar (e.g. 3 of 6 images done). */
  current?: number;
  /** Denominator — when > 0 alongside `current` we render a bar. */
  total?: number;
  /** Per-slide status list; omitted for non-image phases. */
  slides?: SlideProgressItem[];
}

/**
 * The inner card shown under the "currently processing" header during
 * an active phase. Aggregates label, optional detail line, a current/
 * total progress bar for quantifiable phases, and the per-slide grid
 * for phase 5.
 */
export function PhaseProgressDetail({
  label,
  detail,
  current,
  total,
  slides,
}: PhaseProgressDetailProps) {
  const hasProgressBar =
    typeof current === "number" && typeof total === "number" && total > 0;
  const percentComplete = hasProgressBar
    ? Math.round((current / total) * 100)
    : 0;
  const barWidth = hasProgressBar ? Math.min(100, (current / total) * 100) : 0;

  return (
    <div className="space-y-2 rounded-md border border-[var(--color-border)] bg-[var(--color-background)] p-3">
      <p
        className="text-[var(--color-text)] text-sm"
        data-testid="phase-progress-label"
      >
        {label}
      </p>
      {detail ? (
        <p className="text-[var(--color-text-muted)] text-xs italic">
          {detail}
        </p>
      ) : null}
      {hasProgressBar ? (
        <div className="space-y-1">
          <div className="flex justify-between text-[var(--color-text-muted)] text-xs tabular-nums">
            <span>
              {current} / {total}
            </span>
            <span>{percentComplete}%</span>
          </div>
          <div className="h-1 overflow-hidden rounded-full bg-[var(--color-border)]">
            <div
              className="h-full bg-[var(--color-primary)] transition-all"
              style={{ width: `${barWidth}%` }}
              data-testid="phase-progress-bar"
            />
          </div>
        </div>
      ) : null}
      {slides && slides.length > 0 ? (
        <SlideProgressGrid slides={slides} />
      ) : null}
    </div>
  );
}
