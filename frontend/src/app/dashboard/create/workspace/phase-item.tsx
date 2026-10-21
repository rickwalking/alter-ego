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

/** Circle style: completed, running, or pending. */
function phaseCircleClass(isPast: boolean, isActive: boolean): string {
  if (isPast) {
    return "bg-neon-cyan text-bg-deep";
  }
  if (isActive) {
    return "border-2 border-neon-cyan text-neon-cyan";
  }
  return "border border-neon-card-border text-text-muted";
}

/** Circle content: a check when completed, a spinner while running, else the 1-based number. */
function phaseMarker(
  isPast: boolean,
  isActive: boolean,
  index: number,
): React.ReactElement {
  if (isPast) {
    return <CheckIcon testId="phase-check" />;
  }
  if (isActive) {
    return <Spinner small />;
  }
  return <>{index + 1}</>;
}

/** Label style: running phases are accented, completed ones are primary text. */
function phaseLabelClass(isActive: boolean, isPast: boolean): string {
  if (isActive) {
    return "font-medium text-neon-cyan";
  }
  if (isPast) {
    return "text-text-primary";
  }
  return "text-text-muted";
}

/**
 * One row of the vertical pipeline checklist. Rendered by
 * `CarouselProgress` inside a flex column, one per phase in
 * `PIPELINE_PHASES`.
 */
export function PhaseItem({
  phase,
  isActive,
  isPast,
  index,
}: Readonly<PhaseItemProps>) {
  const t = useTranslations("create");

  return (
    <div
      className="flex items-center gap-3"
      data-testid={`phase-item-${phase}`}
    >
      <div
        className={`flex h-6 w-6 items-center justify-center rounded-full text-xs font-bold transition-colors ${phaseCircleClass(isPast, isActive)}`}
        aria-current={isActive ? "step" : undefined}
      >
        {phaseMarker(isPast, isActive, index)}
      </div>
      <span
        data-testid={`phase-label-${phase}`}
        className={`text-sm ${phaseLabelClass(isActive, isPast)}`}
      >
        {t(`progress.phases.${phase}`)}
      </span>
    </div>
  );
}
