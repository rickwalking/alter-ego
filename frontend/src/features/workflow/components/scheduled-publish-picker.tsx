"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button, Input } from "@/components/ui";
import { Label } from "@/components/ui/label";
import { WORKFLOW_API } from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type ScheduledPublishPickerProps = {
  postId: string;
  onScheduled?: () => void;
};

export function ScheduledPublishPicker({ postId, onScheduled }: ScheduledPublishPickerProps) {
  const t = useTranslations("workflow.schedule");
  const [datetime, setDatetime] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleSchedule = async () => {
    if (!datetime) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const response = await authenticatedFetch(WORKFLOW_API.BLOG_SCHEDULE(postId), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ scheduled_publish_at: new Date(datetime).toISOString() }),
      });
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
        <Label htmlFor="schedule-datetime">{t("publishAt")}</Label>
        <Input
          id="schedule-datetime"
          type="datetime-local"
          value={datetime}
          onChange={(e) => setDatetime(e.target.value)}
        />
      </div>
      <Button onClick={() => void handleSchedule()} disabled={submitting || !datetime}>
        {submitting ? t("scheduling") : t("schedule")}
      </Button>
      {message && <p className="text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}
