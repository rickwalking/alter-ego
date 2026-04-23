import type { SlideGenerationStatus } from "@/constants/create";
import { SLIDE_GENERATION_STATUS } from "@/constants/create";

/** Generic checkmark — used for completed phases and done-slide badges. */
export function CheckIcon({ testId }: { testId?: string } = {}): React.ReactElement {
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

/** Filled-triangle warning sign. Sits in the error callout. */
export function ErrorIcon(): React.ReactElement {
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

/** Circle-exclamation — used for the stalled-phase warning. */
export function WarningIcon(): React.ReactElement {
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

/**
 * Generic spinner. `small` renders a 3×3 version used inline inside
 * circles and per-slide status badges; the default 4×4 is for header
 * contexts.
 */
export function Spinner({ small }: { small?: boolean } = {}): React.ReactElement {
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

/** Dispatches to the right per-slide icon variant for a given status. */
export function SlideStatusIcon({
  status,
}: {
  status: SlideGenerationStatus;
}): React.ReactElement {
  return SLIDE_STATUS_ICON[status]();
}
