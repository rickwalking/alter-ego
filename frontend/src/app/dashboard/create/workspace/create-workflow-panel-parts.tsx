"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { EDITORIAL_WORKFLOW_TRANSPORT_MODE } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { CreateRunProgressBanner } from "@/app/dashboard/create/workspace/create-run-progress-banner";
import { WorkflowStatusBadge } from "@/app/dashboard/create/workspace/workflow-status-badge";
import { CreateStepHistoryPanel } from "@/app/dashboard/create/workspace/create-step-history-panel";
import { WorkflowLiveUpdatesDisconnected } from "@/app/dashboard/create/workspace/workflow-live-updates-disconnected";
import { usePhaseLabel } from "@/app/dashboard/create/workspace/editorial-phase-labels";
import {
  CREATE_STEP_TO_EDITORIAL_PHASE,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import type { EditorialWorkflowState } from "@/modules/publishing";
import type { CreateWorkflowApi } from "./create-workflow-panel-state";

const PANEL_FRAME_STYLE = {
  background: "var(--bg-card, #0d1324)",
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export function WorkflowPanelFrame({
  children,
}: {
  children: React.ReactNode;
}): React.JSX.Element {
  return (
    <div className="space-y-4" style={PANEL_FRAME_STYLE}>
      {children}
    </div>
  );
}

/**
 * AE-0315: the live in-progress banner on EVERY step while a run executes;
 * AE-0440: when the stream gave up, say so instead of going stale.
 */
export function WorkflowRunNotices({
  workflow,
}: {
  workflow: CreateWorkflowApi;
}): React.JSX.Element {
  const { state, loading, refreshState } = workflow;
  return (
    <>
      {state?.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS ? (
        <CreateRunProgressBanner
          currentPhase={state.current_phase}
          runStartedAt={state.run_started_at}
          runStage={state.run_stage}
          runningAction={workflow.runningAction}
          onCheckAgain={() => {
            void refreshState();
          }}
          checkAgainDisabled={loading}
        />
      ) : null}
      {workflow.transportMode ===
      EDITORIAL_WORKFLOW_TRANSPORT_MODE.DISCONNECTED ? (
        <WorkflowLiveUpdatesDisconnected
          onRetry={workflow.reconnectLiveUpdates}
        />
      ) : null}
    </>
  );
}

/** A completed step: its read-only snapshot. */
export function HistoricalStepView({
  workflow,
  viewStepId,
  state,
}: {
  workflow: CreateWorkflowApi;
  viewStepId: CreateStepId;
  state: EditorialWorkflowState;
}): React.JSX.Element {
  const tCreate = useTranslations("create.stepHistory");
  const phaseLabel = usePhaseLabel();
  const viewPhase = CREATE_STEP_TO_EDITORIAL_PHASE[viewStepId];
  return (
    <WorkflowPanelFrame>
      <WorkflowRunNotices workflow={workflow} />
      <p className="text-sm" style={{ color: "rgba(255,255,255,0.55)" }}>
        {tCreate("historicalHint", {
          phase: phaseLabel(viewPhase ?? viewStepId),
        })}
      </p>
      <CreateStepHistoryPanel viewStepId={viewStepId} state={state} />
    </WorkflowPanelFrame>
  );
}

/** Title, the polling-fallback badge and the current phase status. */
export function WorkflowPanelHeader({
  workflow,
}: {
  workflow: CreateWorkflowApi;
}): React.JSX.Element {
  const t = useTranslations("editorialWorkflow");
  const phaseLabel = usePhaseLabel();
  const { state } = workflow;
  return (
    <div className="flex items-center justify-between gap-2">
      <h3 className="font-semibold">{t("title")}</h3>
      <div className="flex items-center gap-2">
        {workflow.transportMode ===
          EDITORIAL_WORKFLOW_TRANSPORT_MODE.POLLING_FALLBACK && (
          <NeonBadge variant="outline">
            {t("transport.pollingFallback")}
          </NeonBadge>
        )}
        {workflow.hasActiveWorkflow && (
          <WorkflowStatusBadge
            status={state?.phase_status ?? null}
            label={phaseLabel(state?.current_phase)}
          />
        )}
      </div>
    </div>
  );
}

/** The phases seen so far, the current one highlighted. */
export function PhaseEventBadges({
  phaseEvents,
  currentPhase,
}: {
  phaseEvents: string[];
  currentPhase: string | undefined;
}): React.JSX.Element | null {
  const phaseLabel = usePhaseLabel();
  if (phaseEvents.length === 0) {
    return null;
  }
  return (
    <div className="flex flex-wrap gap-1">
      {phaseEvents.map((phase) => (
        <NeonBadge
          key={phase}
          variant={phase === currentPhase ? "default" : "outline"}
        >
          {phaseLabel(phase)}
        </NeonBadge>
      ))}
    </div>
  );
}

export function WorkflowErrorAlert({
  error,
}: {
  error: string | null;
}): React.JSX.Element | null {
  if (!error) {
    return null;
  }
  return (
    <NeonAlert variant="destructive">
      <NeonAlertDescription>{error}</NeonAlertDescription>
    </NeonAlert>
  );
}
