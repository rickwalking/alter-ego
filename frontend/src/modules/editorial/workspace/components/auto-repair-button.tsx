"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { HTTP_STATUS } from "@/constants/api";
import { EDITORIAL_WORKFLOW_CONFLICT_CODES } from "@/constants/editorial-workflow";
import { ApiError } from "@/lib/api-client";
import {
  useRepairCarousel,
  type RepairCarouselResponse,
  type RepairSlideDiff,
} from "@/modules/editorial/workspace/hooks/use-repair-carousel";
import type { AutoRepairButtonProps } from "./types";

function isRunInProgress(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.status === HTTP_STATUS.CONFLICT &&
    error.code === EDITORIAL_WORKFLOW_CONFLICT_CODES.RUN_IN_PROGRESS
  );
}

function fixedDiffs(response: RepairCarouselResponse): RepairSlideDiff[] {
  return response.repaired.filter((diff) => diff.repaired);
}

export function AutoRepairButton({
  projectId,
  onRepaired,
  onRepublishNeeded,
}: AutoRepairButtonProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review.autoRepair");
  const repair = useRepairCarousel();
  const [summary, setSummary] = useState<RepairSlideDiff[] | null>(null);
  const [inProgress, setInProgress] = useState(false);

  const finish = useCallback(
    (response: RepairCarouselResponse): void => {
      setSummary(fixedDiffs(response));
      if (response.needs_republish && onRepublishNeeded) {
        onRepublishNeeded();
        return;
      }
      onRepaired?.();
    },
    [onRepaired, onRepublishNeeded],
  );

  const handleClick = useCallback(() => {
    setInProgress(false);
    setSummary(null);
    repair.reset();
    repair.mutate(
      { projectId },
      {
        onSuccess: finish,
        onError: (error) => {
          if (isRunInProgress(error)) {
            setInProgress(true);
            onRepaired?.();
          }
        },
      },
    );
  }, [finish, onRepaired, projectId, repair]);

  return (
    <div className="space-y-2" data-testid="auto-repair">
      <NeonButton size="sm" onClick={handleClick} disabled={repair.isPending}>
        {repair.isPending ? t("pending") : t("button")}
      </NeonButton>
      {inProgress && (
        <span className="text-[var(--color-text-muted)] text-xs" role="status">
          {t("conflictInProgress")}
        </span>
      )}
      {repair.isError && !inProgress && (
        <span className="text-destructive text-xs" role="alert">
          {t("failed")}
        </span>
      )}
      {summary !== null && !inProgress && (
        <RepairSummary diffs={summary} noChangesLabel={t("noChanges")} />
      )}
    </div>
  );
}

function RepairSummary({
  diffs,
  noChangesLabel,
}: {
  diffs: RepairSlideDiff[];
  noChangesLabel: string;
}): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review.autoRepair");
  if (diffs.length === 0) {
    return (
      <p className="text-[var(--color-text-muted)] text-xs" role="status">
        {noChangesLabel}
      </p>
    );
  }
  return (
    <ul
      className="space-y-1 text-xs"
      data-testid="repair-summary"
      role="status"
    >
      {diffs.map((diff) => (
        <li
          key={`${diff.slide_index ?? "all"}-${diff.locale ?? "locale"}`}
          className="text-[var(--color-text-muted)]"
        >
          {t("fixedSlide", {
            index: diff.slide_index ?? 0,
            locale: (diff.locale ?? "").toUpperCase(),
            codes: diff.repaired_codes.join(", "),
          })}
        </li>
      ))}
    </ul>
  );
}
