import type {
  GenerationLogEvent,
  GenerationLogPage,
  GenerationLogRun,
} from "@/schemas/carousel-generation-log";

const MS_PER_SECOND = 1000;
const SECONDS_PER_MINUTE = 60;
const SINGLE_DIGIT_SECONDS = 10;

export interface GenerationLogPhaseGroup {
  phase: string | null;
  events: GenerationLogEvent[];
}

export interface GenerationLogRunGroup {
  run: GenerationLogRun;
  phases: GenerationLogPhaseGroup[];
}

interface MutableRunGroup {
  run: GenerationLogRun;
  events: GenerationLogEvent[];
}

export function groupGenerationLogPages(
  pages: GenerationLogPage[],
): GenerationLogRunGroup[] {
  const grouped = new Map<string, MutableRunGroup>();
  const eventIds = new Set<string>();
  for (const page of pages) {
    for (const run of page.runs) {
      if (!grouped.has(run.id)) {
        grouped.set(run.id, { run, events: [] });
      }
    }
    for (const event of page.events) {
      const run = grouped.get(event.generation_run_id);
      if (run && !eventIds.has(event.id)) {
        run.events.push(event);
        eventIds.add(event.id);
      }
    }
  }
  return [...grouped.values()]
    .sort((left, right) =>
      right.run.queued_at.localeCompare(left.run.queued_at),
    )
    .map(({ run, events }) => ({ run, phases: phaseGroups(events) }));
}

export function formatGenerationDuration(durationMs: number | null): string {
  if (durationMs === null) {
    return "—";
  }
  if (durationMs < MS_PER_SECOND) {
    return `${durationMs} ms`;
  }
  const seconds = durationMs / MS_PER_SECOND;
  const roundedSeconds = Math.round(seconds);
  if (roundedSeconds < SECONDS_PER_MINUTE) {
    const precision = seconds < SINGLE_DIGIT_SECONDS ? 1 : 0;
    return `${seconds.toFixed(precision)} s`;
  }
  const minutes = Math.floor(roundedSeconds / SECONDS_PER_MINUTE);
  return `${minutes} min ${roundedSeconds % SECONDS_PER_MINUTE} s`;
}

export function generationPhaseBase(phase: string): string {
  return phase.split(":").at(-1) ?? phase;
}

function phaseGroups(events: GenerationLogEvent[]): GenerationLogPhaseGroup[] {
  const phases = new Map<string, GenerationLogEvent[]>();
  const ordered = [...events].sort(
    (left, right) =>
      left.occurred_at.localeCompare(right.occurred_at) ||
      left.id.localeCompare(right.id),
  );
  for (const event of ordered) {
    const key = event.phase ?? "";
    phases.set(key, [...(phases.get(key) ?? []), event]);
  }
  return [...phases.entries()].map(([phase, items]) => ({
    phase: phase || null,
    events: items,
  }));
}
