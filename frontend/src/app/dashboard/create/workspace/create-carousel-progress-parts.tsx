"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";

import { NEON_AMBER, NEON_AMBER_DIM } from "@/constants/neon";

import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";

import { ErrorIcon, WarningIcon } from "./progress-icons";
import { WorkflowStatusBadge } from "./workflow-status-badge";
import { WORKFLOW_STATUS_COMPLETED } from "./workflow-status";

export function CompleteCard() {
  const t = useTranslations("create");
  return (
    <div className="rounded-lg border border-neon-card-border bg-bg-card p-4">
      <div className="flex items-center gap-2">
        <WorkflowStatusBadge status={WORKFLOW_STATUS_COMPLETED} />
        <span className="font-medium text-text-primary">
          {t("progress.complete")}
        </span>
      </div>
    </div>
  );
}

export function ErrorCard({
  errorMessage,
}: Readonly<{ errorMessage?: string | null }>) {
  const t = useTranslations("create");
  return (
    <NeonAlert variant="destructive">
      <div className="flex items-start gap-2">
        <ErrorIcon />
        <div className="flex-1 space-y-1">
          <span className="font-medium">{t("progress.failed")}</span>
          {errorMessage ? (
            <NeonAlertDescription className="break-words font-mono text-xs">
              {errorMessage}
            </NeonAlertDescription>
          ) : null}
        </div>
      </div>
    </NeonAlert>
  );
}

export function StalledWarning({
  stalledSeconds,
}: Readonly<{ stalledSeconds: number }>) {
  const t = useTranslations("create");
  return (
    <div
      className="flex items-start gap-2 rounded-md p-2 text-xs"
      style={{ background: NEON_AMBER_DIM, color: NEON_AMBER }}
    >
      <WarningIcon />
      <span>
        {t("progress.stalled", { seconds: Math.floor(stalledSeconds) })}
      </span>
    </div>
  );
}

/**
 * Seconds since the last backend update. Frozen when the pipeline
 * terminates. Backend emits naive ISO timestamps that are actually UTC;
 * we append "Z" when no offset is present so `new Date(...)` treats
 * them as UTC instead of local time.
 */
export function useStalledSeconds(
  updatedAt: string | undefined,
  frozen: boolean,
): number {
  const [, setTick] = useState(0);

  useEffect(() => {
    if (!updatedAt || frozen) {
      return;
    }
    const id = window.setInterval(() => setTick((tick) => tick + 1), 1000);
    return () => window.clearInterval(id);
  }, [updatedAt, frozen]);

  if (!updatedAt || frozen) {
    return 0;
  }

  return secondsSince(updatedAt);
}

export function secondsSince(updatedAt: string): number {
  const normalized = /[zZ]|(?:[+-]\d{2}:?\d{2}$)/.test(updatedAt)
    ? updatedAt
    : `${updatedAt}Z`;
  const referenceMs = new Date(normalized).getTime();
  return Math.max(0, (Date.now() - referenceMs) / 1000);
}

export function formatElapsed(seconds: number): string {
  if (seconds < 60) return `${Math.floor(seconds)}s`;
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}m ${s.toString().padStart(2, "0")}s`;
}
