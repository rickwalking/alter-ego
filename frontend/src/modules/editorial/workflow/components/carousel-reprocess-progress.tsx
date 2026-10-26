"use client";

import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { TEXT_MUTED } from "@/constants/neon";
import { QUEUE_STATUS, WORKFLOW_PHASES } from "@/constants/workflow";
import type { CarouselReprocessProgressProps } from "./types";

const SECONDS_PER_MINUTE = 60;
const KNOWN_PHASES: ReadonlySet<string> = new Set([
  ...WORKFLOW_PHASES,
  EDITORIAL_PHASES.PUBLISHED,
]);

function FailureProgress({
  capability,
}: Readonly<CarouselReprocessProgressProps>): React.ReactElement {
  const t = useTranslations("workflow.reprocess");
  return (
    <NeonAlert variant="destructive">
      <NeonAlertDescription>
        {capability.last_error_code
          ? t("progress.failedWithCode", { code: capability.last_error_code })
          : t("progress.failed")}
      </NeonAlertDescription>
    </NeonAlert>
  );
}

function RunningProgress({
  capability,
}: Readonly<CarouselReprocessProgressProps>): React.ReactElement {
  const t = useTranslations("workflow.reprocess");
  const tPhase = useTranslations("create.phases");
  let phaseLabel = capability.last_phase;
  if (phaseLabel && KNOWN_PHASES.has(phaseLabel)) {
    phaseLabel = tPhase(phaseLabel);
  }
  return (
    <p role="status" className="text-xs" style={{ color: TEXT_MUTED }}>
      {phaseLabel
        ? t("progress.running", { phase: phaseLabel })
        : t("progress.runningUnknown")}
    </p>
  );
}

function QueuedProgress({
  capability,
}: Readonly<CarouselReprocessProgressProps>): React.ReactElement {
  const t = useTranslations("workflow.reprocess");
  const parts: string[] = [];
  if (capability.status === QUEUE_STATUS.RETRY_WAIT) {
    parts.push(t("progress.retryWait"));
  } else {
    parts.push(t("progress.queued"));
  }
  if (capability.position !== null) {
    parts.push(t("progress.position", { position: capability.position }));
  }
  if (capability.eta_seconds !== null) {
    const minutes = Math.max(
      0,
      Math.ceil(capability.eta_seconds / SECONDS_PER_MINUTE),
    );
    parts.push(t("progress.eta", { minutes }));
  }
  return (
    <p role="status" className="text-xs" style={{ color: TEXT_MUTED }}>
      {parts.join(" · ")}
    </p>
  );
}

export function CarouselReprocessProgress({
  capability,
}: Readonly<CarouselReprocessProgressProps>): React.ReactElement | null {
  if (capability.status === QUEUE_STATUS.DEAD_LETTER) {
    return <FailureProgress capability={capability} />;
  }
  if (capability.status === QUEUE_STATUS.RUNNING) {
    return <RunningProgress capability={capability} />;
  }
  if (
    capability.status === QUEUE_STATUS.QUEUED ||
    capability.status === QUEUE_STATUS.RETRY_WAIT
  ) {
    return <QueuedProgress capability={capability} />;
  }
  return null;
}
