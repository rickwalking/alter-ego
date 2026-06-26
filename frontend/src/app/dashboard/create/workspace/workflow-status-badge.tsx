"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import type { NeonBadgeSize } from "@/schemas/neon-badge";
import {
  resolveWorkflowStatusVisual,
  titlecaseStatus,
} from "@/app/dashboard/create/workspace/workflow-status";

export interface WorkflowStatusBadgeProps {
  status: string | null | undefined;
  /**
   * Override the displayed label while keeping the semantic colour — e.g. show a
   * phase name coloured by its run status. Defaults to the status' own label.
   */
  label?: string;
  size?: NeonBadgeSize;
}

/**
 * The v2 status indicator for the create-carousel flow: a `NeonBadge` whose
 * colour, live dot, and label are derived from the workflow status, so the same
 * status looks identical everywhere it appears. Status is conveyed by text +
 * colour + dot (never colour alone): even when a `label` override shows a phase
 * name, the accessible name still includes the status word so screen-reader
 * users don't lose it to colour alone.
 *
 * `role="status"` (a polite live region) is applied ONLY when the badge IS the
 * status (no label override); a labelled chip (phase name coloured by status)
 * renders a plain span so it doesn't add a redundant live region per poll.
 */
export function WorkflowStatusBadge({
  status,
  label,
  size = "sm",
}: WorkflowStatusBadgeProps): React.ReactElement {
  const t = useTranslations("create");
  const { variant, pulse, labelKey } = resolveWorkflowStatusVisual(status);
  const statusText = labelKey
    ? t(`status.${labelKey}`)
    : titlecaseStatus(status);
  const text = label ?? statusText;
  const ariaLabel = label ? `${label}, ${statusText}` : statusText;
  const liveProps = label === undefined ? { role: "status" as const } : {};

  return (
    <NeonBadge
      variant={variant}
      size={size}
      pulse={pulse}
      aria-label={ariaLabel}
      {...liveProps}
    >
      {text}
    </NeonBadge>
  );
}
