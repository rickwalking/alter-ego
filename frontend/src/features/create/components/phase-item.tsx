import { useTranslations } from "next-intl";
import { CheckIcon, Spinner } from "./progress-icons";

interface PhaseItemProps {
  /** Phase identifier — must be a key in the create.progress.phases i18n map. */
  phase: string;
  /** Currently-running phase (spinner, accent color). */
  isActive: boolean;
  /** Completed phase (check icon, muted color). */
  isPast: boolean;
  /** Zero-based index for the number rendered on pending phases. */
  index: number;
}

/**
 * One row of the vertical pipeline checklist. Rendered by
 * `CarouselProgress` inside a flex column, one per phase in
 * `PIPELINE_PHASES`.
 */
export function PhaseItem({ phase, isActive, isPast, index }: PhaseItemProps) {
  const t = useTranslations("create");

  return (
    <div className="flex items-center gap-3" data-testid={`phase-item-${phase}`}>
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
}
