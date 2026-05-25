"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Button, Input } from "@/components/ui";
import { Label } from "@/components/ui/label";
import { WORKFLOW_API } from "@/constants/workflow";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import type { ReviewAssignmentPayload } from "@/features/workflow/types";

type ReviewAssignmentPanelProps = {
  contentId: string;
  contentType: string;
  title: string;
  onAssigned?: () => void;
};

export function ReviewAssignmentPanel({
  contentId,
  contentType,
  title,
  onAssigned,
}: ReviewAssignmentPanelProps) {
  const t = useTranslations("workflow.review");
  const [reviewerId, setReviewerId] = useState("");
  const [deadlineHours, setDeadlineHours] = useState("24");
  const [submitting, setSubmitting] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  const handleAssign = async () => {
    if (!reviewerId.trim()) return;
    setSubmitting(true);
    setMessage(null);
    try {
      const payload: ReviewAssignmentPayload = {
        reviewer_id: reviewerId.trim(),
        content_id: contentId,
        content_type: contentType,
        title,
        deadline_hours: Number(deadlineHours) || 24,
      };
      const response = await authenticatedFetch(WORKFLOW_API.ASSIGN_REVIEW, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      if (!response.ok) {
        throw new Error(t("failed"));
      }
      setMessage(t("assigned"));
      onAssigned?.();
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
        <Label htmlFor="reviewer-id">{t("reviewerId")}</Label>
        <Input
          id="reviewer-id"
          value={reviewerId}
          onChange={(e) => setReviewerId(e.target.value)}
          placeholder={t("reviewerPlaceholder")}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="deadline-hours">{t("deadlineHours")}</Label>
        <Input
          id="deadline-hours"
          type="number"
          min={1}
          value={deadlineHours}
          onChange={(e) => setDeadlineHours(e.target.value)}
        />
      </div>
      <Button
        onClick={() => void handleAssign()}
        disabled={submitting || !reviewerId.trim()}
      >
        {submitting ? t("assigning") : t("assignNotify")}
      </Button>
      {message && <p className="text-sm text-muted-foreground">{message}</p>}
    </div>
  );
}
