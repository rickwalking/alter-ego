"use client";

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
import { resolveStepState } from "@/app/dashboard/create/workspace/step-state-helpers";

const CYAN = NEON_CYAN;
const CYAN_DIM = NEON_CYAN_DIM;
const TEAL = NEON_TEAL;
const TEAL_DIM = NEON_TEAL_DIM;

// Named faint tints (no exact design-system token; palette neon.ts is drift-guarded).
const STEP_NUM_PENDING_BG = "rgba(255,255,255,0.04)";
const STEP_DIVIDER = "rgba(255,255,255,0.04)";
const STEP_ACTIVE_BG = "rgba(0,212,255,0.04)";

export interface CreateProgressStepsProps {
  activeStepId: CreateStepId;
  onStepChange: (stepId: CreateStepId) => void;
  /** When set, marks these steps done (e.g. from workflow phase). */
  completedStepIds?: readonly CreateStepId[];
}

export function CreateProgressSteps({
  activeStepId,
  onStepChange,
  completedStepIds,
}: CreateProgressStepsProps): React.ReactElement {
  const doneSteps = completedStepIds ?? completedStepsBefore(activeStepId);
  return (
    <div
      role="tablist"
      aria-label="Carousel creation steps"
      // Scroll horizontally on mobile instead of clipping/squishing the steps.
      className="mb-7 flex overflow-x-auto rounded-lg"
      style={{
        background: BG_CARD,
        border: `1px solid ${NEON_CARD_BORDER}`,
      }}
    >
      {CREATE_STEPS.map((step) => {
        const visual = resolveStepState(step.id, activeStepId, doneSteps);
        const isActive = visual === "active";
        const isDone = visual === "done";
        const labelColor = isActive ? TEXT : isDone ? TEXT_MUTED : TEXT_DIM;
        const numBackground = isActive
          ? CYAN_DIM
          : isDone
            ? TEAL_DIM
            : STEP_NUM_PENDING_BG;
        const numColor = isActive ? CYAN : isDone ? TEAL : TEXT_DIM;

        return (
          <button
            key={step.id}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`create-step-${step.id}`}
            id={`create-tab-${step.id}`}
            onClick={() => onStepChange(step.id)}
            // shrink-0 + min width so steps scroll (not squish) on mobile;
            // distribute evenly at md+. ≥44px tall on touch devices.
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
            <span className="create-step-label">{step.label}</span>
          </button>
        );
      })}
    </div>
  );
}
