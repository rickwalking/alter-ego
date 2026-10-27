"use client";

import { useLocale, useTranslations } from "next-intl";
import { formatLocaleTime } from "@/lib/locale-format";
import type { GenerationLogEvent } from "@/schemas/carousel-generation-log";
import { formatGenerationDuration } from "./create-generation-log-model";
import { WarningIcon } from "./progress-icons";

const EVENT_TYPES = new Set([
  "run_queued",
  "run_started",
  "run_waiting",
  "run_succeeded",
  "run_retry",
  "run_dead_letter",
  "run_lost",
  "phase_started",
  "phase_succeeded",
  "phase_failed",
  "phase_artifacts",
  "persona_scored",
  "content_gate",
  "image_job_started",
  "image_job_reused",
  "image_job_succeeded",
  "image_job_failed",
  "image_reused",
  "image_slide_succeeded",
  "image_slide_failed",
  "pdf_succeeded",
  "pdf_failed",
  "recovery_reaped",
  "workflow_succeeded",
  "workflow_failed",
]);
const OUTCOMES = new Set([
  "queued",
  "running",
  "succeeded",
  "failed",
  "retry_wait",
  "dead_letter",
  "recovered",
  "reused",
  "warning",
]);

interface GenerationEventRowProps {
  event: GenerationLogEvent;
}

function outcomeClass(failed: boolean, warning: boolean): string {
  if (failed) {
    return "border-neon-red text-neon-red";
  }
  if (warning) {
    return "border-neon-amber text-neon-amber";
  }
  return "border-white/20 text-text-dim";
}

export function GenerationEventRow({
  event,
}: Readonly<GenerationEventRowProps>) {
  const t = useTranslations("create.generationLog");
  const locale = useLocale();
  const label = EVENT_TYPES.has(event.event_type)
    ? t(`events.${event.event_type}`)
    : event.event_type.replaceAll("_", " ");
  const outcome = OUTCOMES.has(event.outcome)
    ? t(`outcomes.${event.outcome}`)
    : event.outcome;
  const failed = event.outcome === "failed" || event.outcome === "dead_letter";
  const warning = event.outcome === "warning";
  return (
    <li className="space-y-1" data-outcome={event.outcome}>
      <div className="flex items-start gap-2">
        <span className="min-w-0 flex-1 text-text-primary">{label}</span>
        <span
          className={`inline-flex shrink-0 items-center gap-1 rounded border px-1 font-semibold ${outcomeClass(failed, warning)}`}
        >
          {warning && <WarningIcon />}
          {outcome}
        </span>
        <span className="ml-auto shrink-0 text-right tabular-nums">
          {formatGenerationDuration(event.duration_ms)}
        </span>
      </div>
      <div className="flex flex-wrap items-center gap-2 text-text-dim">
        <time dateTime={event.occurred_at}>
          {formatLocaleTime(event.occurred_at, locale)}
        </time>
        {event.attempt !== null && (
          <span>{t("attempt", { count: event.attempt })}</span>
        )}
        {event.error_code && <span>{event.error_code}</span>}
        {event.langfuse_trace_url && (
          <a
            href={event.langfuse_trace_url}
            target="_blank"
            rel="noreferrer"
            className="text-neon-cyan underline"
          >
            {t("openTrace")}
          </a>
        )}
      </div>
      <EventDetails event={event} />
    </li>
  );
}

function EventDetails({ event }: Readonly<GenerationEventRowProps>) {
  const t = useTranslations("create.generationLog");
  const { details } = event;
  const lines: string[] = [];
  if (typeof details.violation_count === "number") {
    lines.push(t("details.violations", { count: details.violation_count }));
  }
  if (typeof details.lowest_score === "number") {
    lines.push(t("details.personaScore", { score: details.lowest_score }));
  }
  if (typeof details.image_job_id === "string") {
    lines.push(t("details.imageJob", { id: details.image_job_id }));
  }
  if (typeof details.size === "string" || typeof details.model === "string") {
    lines.push(
      [details.size, details.model]
        .filter((value) => typeof value === "string")
        .join(" · "),
    );
  }
  if (typeof details.delay_seconds === "number") {
    lines.push(t("details.retryDelay", { seconds: details.delay_seconds }));
  }
  if (typeof details.page_count === "number") {
    lines.push(t("details.pages", { count: details.page_count }));
  }
  if (lines.length === 0) {
    return null;
  }
  return <p className="break-all text-text-dim">{lines.join(" · ")}</p>;
}
