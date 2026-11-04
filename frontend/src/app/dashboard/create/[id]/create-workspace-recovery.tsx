"use client";

import { useTranslations } from "next-intl";
import { NeonToast } from "@/components/molecules/neon-toast";
import {
  CarouselReprocess,
  CarouselRetryAction,
  useCarouselReprocess,
  useCarouselRetry,
} from "@/modules/editorial";
import type { CarouselReprocessState } from "@/modules/editorial";
import type { WorkspaceRecovery } from "./types";
import type { CreateWorkspace } from "./use-create-workspace";

function shouldShowReprocess(reprocess: CarouselReprocessState): boolean {
  if (reprocess.pending || reprocess.error !== null) return true;
  return (
    typeof reprocess.capability?.stuck_kind === "string" ||
    reprocess.progressVisible
  );
}

export function useWorkspaceRecovery(
  workspace: CreateWorkspace,
): WorkspaceRecovery {
  const t = useTranslations("workflow.retry");
  const { editorialWorkflow, projectId, starter } = workspace;
  const state = editorialWorkflow.state;
  const hasPhase = Boolean(state?.current_phase);
  const reprocess = useCarouselReprocess({
    projectId,
    enabled: hasPhase,
    fallbackExpectedVersion: state?.lock_version,
    refreshWorkflow: editorialWorkflow.refreshState,
  });
  const retry = useCarouselRetry({
    projectId,
    enabled: hasPhase && !starter.retrying,
    workflowState: state,
    refreshWorkflow: editorialWorkflow.refreshState,
  });
  const showReprocess = shouldShowReprocess(reprocess);
  return {
    reprocessControl: showReprocess ? (
      <CarouselReprocess
        capability={reprocess.capability}
        pending={reprocess.pending}
        canSubmit={reprocess.canSubmit}
        error={reprocess.error}
        onReprocess={() => {
          void reprocess.reprocess();
        }}
      />
    ) : null,
    retryControl:
      retry.visible && !showReprocess ? (
        <CarouselRetryAction
          capability={retry.capability}
          pending={retry.pending}
          canSubmit={retry.canSubmit}
          error={retry.error}
          onRetry={() => {
            void retry.retry();
          }}
        />
      ) : null,
    retryPending: retry.pending,
    startOverLabel: t("startOver"),
    retryToast: retry.toast ? (
      <NeonToast
        key={retry.toast.id}
        message={retry.toast.message}
        variant={retry.toast.variant}
        onDismiss={retry.dismissToast}
      />
    ) : null,
  };
}
