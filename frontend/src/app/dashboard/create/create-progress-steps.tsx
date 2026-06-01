"use client";

import {
  BG_CARD,
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

const CYAN = NEON_CYAN;
const CYAN_DIM = NEON_CYAN_DIM;
const TEAL = NEON_TEAL;
const TEAL_DIM = NEON_TEAL_DIM;

export interface CreateProgressStepsProps {
  activeStepId: CreateStepId;
  onStepChange: (stepId: CreateStepId) => void;
  /** When set, marks these steps done (e.g. from workflow phase). */
  completedStepIds?: readonly CreateStepId[];
}

type StepVisualState = "active" | "done" | "pending";

function resolveStepState(
  stepId: CreateStepId,
  activeStepId: CreateStepId,
  completedStepIds: readonly CreateStepId[],
): StepVisualState {
  if (stepId === activeStepId) {
    return "active";
  }
  if (completedStepIds.includes(stepId)) {
    return "done";
  }
  return "pending";
}

export function CreateProgressSteps({
  activeStepId,
  onStepChange,
  completedStepIds,
}: CreateProgressStepsProps): React.ReactElement {
  const doneSteps =
    completedStepIds ?? completedStepsBefore(activeStepId);
  return (
    <div
      role="tablist"
      aria-label="Carousel creation steps"
      style={{
        display: "flex",
        marginBottom: "28px",
        background: BG_CARD,
        borderRadius: "8px",
        border: "1px solid rgba(255,255,255,0.06)",
        overflow: "hidden",
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
            : "rgba(255,255,255,0.04)";
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
            style={{
              flex: 1,
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
              fontSize: "12px",
              color: labelColor,
              border: "none",
              borderRight:
                step.num < CREATE_STEPS.length
                  ? "1px solid rgba(255,255,255,0.04)"
                  : "none",
              background: isActive ? "rgba(0,212,255,0.04)" : "transparent",
              cursor: "pointer",
              fontFamily: "inherit",
              textAlign: "left",
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
