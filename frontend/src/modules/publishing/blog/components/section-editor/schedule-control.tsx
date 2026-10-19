"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { BLOG_EDITOR_I18N_NAMESPACE } from "@/constants/blog-editor";
import type { ScheduleControlProps } from "./types";

const SCHEDULE_INPUT_ID = "blog-schedule-at";

/**
 * Schedule an approved post (AE-0424): a local date/time sent as UTC ISO; the
 * API rejects a time inside the minimum lead time (shown as an error).
 * "Cancel schedule" clears it and the post stays approved.
 */
export function ScheduleControl({
  scheduledPublishAt,
  disabled,
  onSchedule,
  onCancelSchedule,
}: ScheduleControlProps): React.ReactElement {
  const t = useTranslations(BLOG_EDITOR_I18N_NAMESPACE);
  const [when, setWhen] = useState("");
  if (scheduledPublishAt) {
    return (
      <div className="flex flex-wrap items-center gap-2">
        <span className="text-xs">
          {t("review.scheduledFor", {
            date: new Date(scheduledPublishAt).toLocaleString(),
          })}
        </span>
        <NeonButton
          size="sm"
          variant="outline"
          disabled={disabled}
          onClick={onCancelSchedule}
        >
          {t("review.cancelSchedule")}
        </NeonButton>
      </div>
    );
  }
  return (
    <div className="flex flex-wrap items-end gap-2">
      <div>
        <label
          htmlFor={SCHEDULE_INPUT_ID}
          className="mb-1 block text-xs font-semibold text-text-muted"
        >
          {t("review.scheduleAt")}
        </label>
        <NeonInput
          id={SCHEDULE_INPUT_ID}
          type="datetime-local"
          value={when}
          disabled={disabled}
          onChange={(e) => setWhen(e.target.value)}
        />
      </div>
      <NeonButton
        size="sm"
        variant="outline"
        disabled={disabled || !when}
        onClick={() => onSchedule(new Date(when).toISOString())}
      >
        {t("review.schedule")}
      </NeonButton>
    </div>
  );
}
