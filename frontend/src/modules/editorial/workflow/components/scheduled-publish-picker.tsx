"use client";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonLabel } from "@/components/atoms/neon-label";
import { WORKFLOW_API } from "@/constants/workflow";
import { useWorkflowPostAction } from "../hooks/use-workflow-post-action";
import type { ScheduledPublishPickerProps } from "./types";

export function ScheduledPublishPicker({
  postId,
  onScheduled,
}: Readonly<ScheduledPublishPickerProps>) {
  const t = useTranslations("workflow.schedule");
  const [datetime, setDatetime] = useState("");
  const { submitting, message, post } = useWorkflowPostAction(
    { success: t("success"), failed: t("failed") },
    onScheduled,
  );

  const handleSchedule = async () => {
    if (!datetime) return;
    await post(WORKFLOW_API.BLOG_SCHEDULE(postId), {
      scheduled_publish_at: new Date(datetime).toISOString(),
    });
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
