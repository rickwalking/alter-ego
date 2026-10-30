"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { BG_CARD, TEXT_DIM } from "@/constants/neon";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";

import { PublishFailedNotice } from "@/modules/publishing";
import type { EditorialWorkflowState } from "@/modules/publishing";
import { carouselDisplayTitle } from "@/lib/carousel-display-title";

import type { LoadedProject } from "./use-publish-page";

export const panelStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export function PublishPageHeading({
  project,
  projectId,
}: Readonly<{
  project: LoadedProject;
  projectId: string;
}>): React.ReactElement {
  const t = useTranslations("publish");
  return (
    <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
      <div>
        <h1 style={{ fontSize: "20px", fontWeight: 700, margin: 0 }}>
          {carouselDisplayTitle(project)}
        </h1>
        <p style={{ fontSize: "13px", color: TEXT_DIM, marginTop: "6px" }}>
          {project.audience} · {project.niche}
        </p>
      </div>
      <Link
        href={`${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=publish`}
        className="inline-flex shrink-0 items-center [@media(pointer:coarse)]:min-h-11"
        style={{ fontSize: "13px", color: "#00d4ff", textDecoration: "none" }}
      >
        {t("backToWorkspace")}
      </Link>
    </div>
  );
}

/** A failed run, or built artifacts awaiting the final approval. */
export function PublishStatusNotices({
  workflowState,
  projectId,
  canPublishToSite,
  artifactsReady,
}: Readonly<{
  workflowState: EditorialWorkflowState | null;
  projectId: string;
  canPublishToSite: boolean;
  artifactsReady: boolean;
}>): React.ReactElement | null {
  const t = useTranslations("publish");
  if (workflowState?.phase_status === WORKFLOW_PHASE_STATUS.FAILED) {
    return canPublishToSite ? null : (
      <PublishFailedNotice
        currentPhase={workflowState.current_phase}
        errorMessage={workflowState.error_message}
        workspaceHref={`${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=outline`}
      />
    );
  }
  if (!artifactsReady || canPublishToSite) {
    return null;
  }
  return (
    <p
      style={{
        ...panelStyle,
        fontSize: "13px",
        color: TEXT_DIM,
        marginBottom: "16px",
      }}
    >
      {t("awaitingFinalApproval")}
    </p>
  );
}

/** The artifacts are not built yet (a failed run shows its own notice). */
export function PublishNotReady({
  workflowState,
  artifactsReady,
}: Readonly<{
  workflowState: EditorialWorkflowState | null;
  artifactsReady: boolean;
}>): React.ReactElement | null {
  const t = useTranslations("publish");
  if (
    artifactsReady ||
    workflowState?.phase_status === WORKFLOW_PHASE_STATUS.FAILED
  ) {
    return null;
  }
  return (
    <div
      role="status"
      data-testid="publish-not-ready"
      style={{ ...panelStyle, fontSize: "13px", color: TEXT_DIM }}
    >
      <p style={{ margin: 0, fontWeight: 600 }}>{t("notReady.title")}</p>
      <p style={{ margin: "6px 0 0" }}>{t("notReady.body")}</p>
    </div>
  );
}

/** The site-publish button, its outcome and, after a success, the public link. */
export function SitePublishBar({
  publishedHref,
  message,
  onPublish,
}: Readonly<{
  publishedHref: string | null;
  message: string | null;
  onPublish: () => void;
}>): React.ReactElement {
  const t = useTranslations("publish");
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        alignItems: "center",
        gap: "12px",
        marginBottom: "16px",
      }}
    >
      <NeonButton size="sm" onClick={onPublish}>
        {t("publishToSite")}
      </NeonButton>
      {message ? (
        <span style={{ fontSize: "13px", color: TEXT_DIM }}>
          {message}{" "}
          {publishedHref ? (
            <Link
              href={publishedHref}
              target="_blank"
              rel="noopener noreferrer"
              style={{ color: "#00d4ff" }}
            >
              {t("sitePublishedLink")}
            </Link>
          ) : null}
        </span>
      ) : null}
    </div>
  );
}
