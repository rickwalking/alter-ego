"use client";

import { useTranslations } from "next-intl";
import {
  BG_CARD,
  NEON_CARD_BORDER,
  NEON_CYAN,
  NEON_CYAN_DIM,
  NEON_TEAL,
  NEON_TEAL_DIM,
  TEXT,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import { CREATE_STEPS } from "@/app/dashboard/create/constants";
import {
  completedStepsBefore,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import {
  resolveStepState,
  type StepVisualState,
} from "@/app/dashboard/create/workspace/step-state-helpers";

const CYAN = NEON_CYAN;
const CYAN_DIM = NEON_CYAN_DIM;
const TEAL = NEON_TEAL;
const TEAL_DIM = NEON_TEAL_DIM;

/**
 * Faint tints local to the stepper: no exact token exists in the Neon palette,
 * so they live here rather than in the drift-guarded neon.ts.
 */
const STEP_NUM_PENDING_BG = "rgba(255,255,255,0.04)";
const STEP_DIVIDER = "rgba(255,255,255,0.04)";

/** Label and step-number colors for each visual step state. */
const STEP_VISUAL_COLORS: Readonly<
  Record<
    StepVisualState,
    { label: string; numBackground: string; numColor: string }
  >
> = {
  active: { label: TEXT, numBackground: CYAN_DIM, numColor: CYAN },
  done: { label: TEXT_MUTED, numBackground: TEAL_DIM, numColor: TEAL },
  pending: {
    label: TEXT_DIM,
    numBackground: STEP_NUM_PENDING_BG,
    numColor: TEXT_DIM,
  },
};
const STEP_ACTIVE_BG = "rgba(0,212,255,0.04)";

export interface CreateProgressStepsProps {
  activeStepId: CreateStepId;
  onStepChange: (stepId: CreateStepId) => void;
  /** When set, marks these steps done (e.g. from workflow phase). */
  completedStepIds?: readonly CreateStepId[];
}

/**
 * Scrolls horizontally on mobile instead of clipping or squishing the steps
 * (each step is shrink-0 with a minimum width, at least 44px tall on touch
 * devices) and distributes the steps evenly at md+.
 */
export function CreateProgressSteps({
  activeStepId,
  onStepChange,
  completedStepIds,
}: Readonly<CreateProgressStepsProps>): React.ReactElement {
  const t = useTranslations("create.steps");
  const doneSteps = completedStepIds ?? completedStepsBefore(activeStepId);
  return (
    <div
      role="tablist"
      aria-label={t("ariaLabel")}
      className="mb-7 flex overflow-x-auto rounded-lg"
      style={{
        background: BG_CARD,
        border: `1px solid ${NEON_CARD_BORDER}`,
      }}
    >
      {CREATE_STEPS.map((step) => {
        const visual = resolveStepState(step.id, activeStepId, doneSteps);
        const isActive = visual === "active";
        const {
          label: labelColor,
          numBackground,
          numColor,
        } = STEP_VISUAL_COLORS[visual];

        return (
          <button
            key={step.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`create-step-${step.id}`}
            id={`create-tab-${step.id}`}
            onClick={() => onStepChange(step.id)}
            className="flex shrink-0 items-center gap-2 px-4 py-3 text-left [@media(pointer:coarse)]:min-h-11 md:flex-1 md:shrink"
            style={{
              fontSize: "12px",
              color: labelColor,
              border: "none",
              borderRight:
                step.num < CREATE_STEPS.length
                  ? `1px solid ${STEP_DIVIDER}`
                  : "none",
              background: isActive ? STEP_ACTIVE_BG : "transparent",
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            <span
              style={{
                width: "20px",
                height: "20px",
                borderRadius: "50%",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                fontSize: "10px",
                fontWeight: 700,
                flexShrink: 0,
                background: numBackground,
                color: numColor,
              }}
            >
              {step.num}
            </span>
            <span className="create-step-label">{t(step.id)}</span>
          </button>
        );
      })}
    </div>
  );
}
