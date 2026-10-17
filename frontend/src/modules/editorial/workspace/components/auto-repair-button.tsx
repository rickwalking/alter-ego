"use client";

import { useCallback, useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { HTTP_STATUS } from "@/constants/api";
import { EDITORIAL_WORKFLOW_CONFLICT_CODES } from "@/constants/editorial-workflow";
import { ApiError } from "@/lib/api-client";
import { REPAIR_STATUS_NOOP } from "@/modules/editorial/workspace/constants";
import { VIOLATION_SEVERITY_WARNING } from "@/modules/editorial/workspace/lib/presentation-review-utils";
import {
  useRepairCarousel,
  type RepairCarouselResponse,
  type RepairSlideDiff,
} from "@/modules/editorial/workspace/hooks/use-repair-carousel";
import type { AutoRepairButtonProps, RepairOutcome } from "./types";

function isRunInProgress(error: unknown): boolean {
  return (
    error instanceof ApiError &&
    error.status === HTTP_STATUS.CONFLICT &&
    error.code === EDITORIAL_WORKFLOW_CONFLICT_CODES.RUN_IN_PROGRESS
  );
}

/**
 * AE-0414 (B09): what the repair fixed AND what it could not fix. The open
 * blockers come from the fresh report; the per-slide ``remaining_codes`` are
 * the fallback when the report carries none.
 */
function repairOutcome(response: RepairCarouselResponse): RepairOutcome {
  const blockers = response.validation.violations.filter(
    (violation) => violation.severity !== VIOLATION_SEVERITY_WARNING,
  ).length;
  const remainingCodes = response.repaired.reduce(
    (total, diff) => total + diff.remaining_codes.length,
    0,
  );
  return {
    fixed: response.repaired.filter((diff) => diff.repaired),
    remaining: blockers > 0 ? blockers : remainingCodes,
  };
}

export function AutoRepairButton({
  projectId,
  onRepaired,
  onRepublishNeeded,
}: AutoRepairButtonProps): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review.autoRepair");
  const repair = useRepairCarousel();
  const [summary, setSummary] = useState<RepairOutcome | null>(null);
  const [inProgress, setInProgress] = useState(false);

  const finish = useCallback(
    (response: RepairCarouselResponse): void => {
      setSummary(repairOutcome(response));
      // A no-op wrote nothing: refreshing would only re-read the same state.
      if (response.status === REPAIR_STATUS_NOOP) {
        return;
      }
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
      {summary !== null && !inProgress && <RepairSummary outcome={summary} />}
    </div>
  );
}

function RepairSummary({
  outcome,
}: {
  outcome: RepairOutcome;
}): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review.autoRepair");
  return (
    <div className="space-y-1">
      {outcome.fixed.length > 0 ? <FixedList diffs={outcome.fixed} /> : null}
      {outcome.remaining > 0 ? (
        <p className="text-destructive text-xs" role="alert">
          {t("remaining", { count: outcome.remaining })}
        </p>
      ) : null}
      {outcome.fixed.length === 0 && outcome.remaining === 0 ? (
        <p className="text-[var(--color-text-muted)] text-xs" role="status">
          {t("noChanges")}
        </p>
      ) : null}
    </div>
  );
}

function FixedList({
  diffs,
}: {
  diffs: RepairSlideDiff[];
}): React.ReactElement {
  const t = useTranslations("editorialWorkflow.review.autoRepair");
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
