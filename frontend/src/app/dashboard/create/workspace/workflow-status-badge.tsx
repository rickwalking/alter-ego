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
 * colour + dot (never colour alone) and announced via `role="status"`.
 */
export function WorkflowStatusBadge({
  status,
  label,
  size = "sm",
}: WorkflowStatusBadgeProps): React.ReactElement {
  const t = useTranslations("create");
  const { variant, pulse, labelKey } = resolveWorkflowStatusVisual(status);
  const text =
    label ?? (labelKey ? t(`status.${labelKey}`) : titlecaseStatus(status));

  return (
    <NeonBadge
      variant={variant}
      size={size}
      pulse={pulse}
      role="status"
      aria-label={text}
    >
      {text}
    </NeonBadge>
  );
}
