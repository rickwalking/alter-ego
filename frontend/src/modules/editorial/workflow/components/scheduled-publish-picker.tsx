"use client";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonLabel } from "@/components/atoms/neon-label";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { WORKFLOW_API } from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type ScheduledPublishPickerProps = {
  postId: string;
  onScheduled?: () => void;
};

export function ScheduledPublishPicker({
  postId,
  onScheduled,
}: ScheduledPublishPickerProps) {
  const t = useTranslations("workflow.schedule");
  const [datetime, setDatetime] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSchedule = async () => {
    if (!datetime) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await authenticatedFetch(
        WORKFLOW_API.BLOG_SCHEDULE(postId),
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            scheduled_publish_at: new Date(datetime).toISOString(),
          }),
        },
      );
      if (!response.ok) {
        throw new Error(t("failed"));
      }
      setMessage(t("success"));
      onScheduled?.();
    } catch (err) {
      setMessage(err instanceof Error ? err.message : t("failed"));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3 rounded-md border p-4">
      <h3 className="font-medium text-sm">{t("title")}</h3>
      <div className="space-y-2">
        <NeonLabel htmlFor="schedule-datetime">{t("publishAt")}</NeonLabel>
        <NeonInput
          id="schedule-datetime"
          type="datetime-local"
          value={datetime}
          onChange={(e) => setDatetime(e.target.value)}
        />
      </div>
      <NeonButton
        onClick={() => void handleSchedule()}
        disabled={submitting || !datetime}
      >
        {submitting ? t("scheduling") : t("schedule")}
      </NeonButton>
      {message && <p className="text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}
