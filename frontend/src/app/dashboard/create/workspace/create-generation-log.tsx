"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { formatLocaleDateTime } from "@/lib/locale-format";
import type { GenerationLogView } from "@/modules/editorial";
import type { GenerationLogRun } from "@/schemas/carousel-generation-log";
import { GenerationPhase } from "./create-generation-log-phase";
import {
  formatGenerationDuration,
  groupGenerationLogPages,
  type GenerationLogRunGroup,
} from "./create-generation-log-model";

const RUN_KINDS = new Set(["workflow_resume", "autopilot_drive"]);
const RUN_STATUSES = new Set([
  "queued",
  "running",
  "retry_wait",
  "succeeded",
  "dead_letter",
  "cancelled",
]);

interface GenerationLogProps {
  query?: GenerationLogView;
}

interface GenerationLogNoticeProps {
  query: GenerationLogView;
  groupCount: number;
}

interface GenerationRunProps {
  group: GenerationLogRunGroup;
  open: boolean;
}

export function CreateGenerationLog({
  query,
}: Readonly<GenerationLogProps>): React.ReactElement | null {
  const t = useTranslations("create.generationLog");
  if (!query) {
    return null;
  }
  const pages = query.data?.pages ?? [];
  const groups = groupGenerationLogPages(pages);
  return (
    <section
      role="log"
      aria-live="off"
      aria-label={t("title")}
      className="space-y-3 rounded-lg border border-white/10 bg-bg-card p-4 text-xs"
    >
      <h3 className="font-bold text-sm text-text-primary">{t("title")}</h3>
      <GenerationLogNotice query={query} groupCount={groups.length} />
      {groups.map((group, index) => (
        <GenerationRun key={group.run.id} group={group} open={index === 0} />
      ))}
      {query.hasNextPage && (
        <NeonButton
          variant="outline"
          size="sm"
          loading={query.isFetchingNextPage}
          onClick={() => void query.fetchNextPage()}
        >
          {t("loadMore")}
        </NeonButton>
      )}
    </section>
  );
}

function GenerationLogNotice({
  query,
  groupCount,
}: Readonly<GenerationLogNoticeProps>): React.ReactElement | null {
  const t = useTranslations("create.generationLog");
  if (query.isError) {
    return (
      <p role="alert" className="text-neon-red">
        {t(groupCount > 0 ? "loadError" : "initialError")}
      </p>
    );
  }
  if (query.isLoading && groupCount === 0) {
    return <p>{t("loading")}</p>;
  }
  if (groupCount === 0) {
    return <p className="text-text-dim">{t("empty")}</p>;
  }
  return null;
}

function GenerationRun({
  group,
  open,
}: Readonly<GenerationRunProps>): React.ReactElement {
  const t = useTranslations("create.generationLog");
  const { run } = group;
  const [expanded, setExpanded] = useState(open);
  const kind = RUN_KINDS.has(run.kind) ? t(`kinds.${run.kind}`) : run.kind;
  const status = RUN_STATUSES.has(run.status)
    ? t(`statuses.${run.status}`)
    : run.status;
  return (
    <details
      open={expanded}
      onToggle={(event) => setExpanded(event.currentTarget.open)}
      className="rounded-md border border-white/10 p-2"
    >
      <summary className="cursor-pointer font-semibold text-text-primary">
        {kind}, {status}
      </summary>
      <div className="mt-2 space-y-2">
        <RunTimes run={run} />
        <p className="text-text-dim">
          {t("attempts", { count: run.attempts })}
          {run.error_code && (
            <span className="ml-2 text-neon-red">
              {t("errorCode", { code: run.error_code })}
            </span>
          )}
        </p>
        {group.phases.map((phase, index) => (
          <GenerationPhase
            key={`${phase.phase ?? "run"}-${index}`}
            group={phase}
          />
        ))}
      </div>
    </details>
  );
}

function RunTimes({ run }: Readonly<{ run: GenerationLogRun }>) {
  const t = useTranslations("create.generationLog");
  const locale = useLocale();
  return (
    <div className="grid gap-1 text-text-dim">
      <span>
        {t("queuedAt")} <Time value={run.queued_at} locale={locale} />
      </span>
      <span>
        {t("startedAt")} <Time value={run.started_at} locale={locale} />
      </span>
      <span>
        {t("finishedAt")} <Time value={run.finished_at} locale={locale} />
        {run.duration_ms !== null && (
          <span className="float-right text-right tabular-nums">
            {formatGenerationDuration(run.duration_ms)}
          </span>
        )}
      </span>
    </div>
  );
}

function Time({
  value,
  locale,
}: Readonly<{ value: string | null; locale: string }>) {
  if (!value) {
    return <span>—</span>;
  }
  return <time dateTime={value}>{formatLocaleDateTime(value, locale)}</time>;
}
