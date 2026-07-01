import type { NeonBadgeVariant } from "@/schemas/neon-badge";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";

/**
 * Visual treatment for a workflow status: a semantic NeonBadge variant, whether
 * the badge shows a live (pulsing) dot, and the i18n label key under
 * `create.status`. `labelKey` is null for an unrecognized status so the badge
 * can fall back to the titlecased raw value.
 */
export interface WorkflowStatusVisual {
  variant: NeonBadgeVariant;
  pulse: boolean;
  labelKey: string | null;
}

/** Additional non-enum statuses the calendar/board surface can emit. */
export const WORKFLOW_STATUS_PUBLISHED = "published";
export const WORKFLOW_STATUS_COMPLETED = "completed";
const STATUS_PUBLISHED = WORKFLOW_STATUS_PUBLISHED;
const STATUS_COMPLETED = WORKFLOW_STATUS_COMPLETED;
const STATUS_DRAFT = "draft";

/**
 * The complete status vocabulary this map may receive (AE-0299). Typed as a
 * closed union so a new status is a compile error here — the same
 * cross-domain-drift failure class AE-0295 fixed for blog statuses.
 */
type KnownWorkflowStatus =
  | (typeof WORKFLOW_PHASE_STATUS)[keyof typeof WORKFLOW_PHASE_STATUS]
  | (typeof EDITORIAL_WORKFLOW_STATUS)[keyof typeof EDITORIAL_WORKFLOW_STATUS]
  | typeof WORKFLOW_STATUS_PUBLISHED
  | typeof WORKFLOW_STATUS_COMPLETED
  | typeof STATUS_DRAFT;

const STATUS_VISUALS: Record<KnownWorkflowStatus, WorkflowStatusVisual> = {
  [WORKFLOW_PHASE_STATUS.PENDING]: {
    variant: "amber",
    pulse: false,
    labelKey: "draft",
  },
  [STATUS_DRAFT]: { variant: "amber", pulse: false, labelKey: "draft" },
  [WORKFLOW_PHASE_STATUS.IN_PROGRESS]: {
    variant: "cyan",
    pulse: true,
    labelKey: "inProgress",
  },
  [WORKFLOW_PHASE_STATUS.AWAITING_HUMAN]: {
    variant: "magenta",
    pulse: false,
    labelKey: "awaitingHuman",
  },
  [WORKFLOW_PHASE_STATUS.APPROVED]: {
    variant: "teal",
    pulse: false,
    labelKey: "approved",
  },
  [EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH]: {
    variant: "teal",
    pulse: false,
    labelKey: "readyToPublish",
  },
  [STATUS_PUBLISHED]: { variant: "green", pulse: false, labelKey: "published" },
  [STATUS_COMPLETED]: { variant: "green", pulse: false, labelKey: "completed" },
  [WORKFLOW_PHASE_STATUS.REJECTED]: {
    variant: "red",
    pulse: false,
    labelKey: "rejected",
  },
  [WORKFLOW_PHASE_STATUS.FAILED]: {
    variant: "red",
    pulse: false,
    labelKey: "failed",
  },
};

/** Draft is the resolved state for a missing/empty status (not-yet-started). */
const EMPTY_STATUS_VISUAL: WorkflowStatusVisual = STATUS_VISUALS[STATUS_DRAFT];

/** Safe default for an unrecognized status: neutral cyan, label from raw value. */
const UNKNOWN_STATUS_VISUAL: WorkflowStatusVisual = {
  variant: "cyan",
  pulse: false,
  labelKey: null,
};

/** Known status vocabulary — exported for the drift-guard unit test (AE-0299). */
export const KNOWN_WORKFLOW_STATUSES: readonly string[] =
  Object.keys(STATUS_VISUALS);

const ERR_UNKNOWN_WORKFLOW_STATUS = "Unknown workflow status";

/**
 * Map a workflow/phase status string to its semantic badge treatment.
 *
 * An unrecognized status THROWS outside production (AE-0299) so drift from a
 * loose-typed path (e.g. a deserialized API string) is observable instead of
 * silently rendering the neutral cyan; the cyan fallback remains only as a
 * last-resort production guard.
 */
export function resolveWorkflowStatusVisual(
  status: string | null | undefined,
): WorkflowStatusVisual {
  if (!status) {
    return EMPTY_STATUS_VISUAL;
  }
  const visual = (STATUS_VISUALS as Record<string, WorkflowStatusVisual>)[
    status
  ];
  if (visual) {
    return visual;
  }
  if (process.env.NODE_ENV !== "production") {
    throw new Error(`${ERR_UNKNOWN_WORKFLOW_STATUS}: ${status}`);
  }
  return UNKNOWN_STATUS_VISUAL;
}

/** Titlecase a raw status token for the unknown-status fallback label. */
export function titlecaseStatus(status: string | null | undefined): string {
  if (!status) {
    return "";
  }
  return status
    .replace(/[_-]+/g, " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}
