"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonButton } from "@/components/atoms/neon-button";
import { BG_CARD, TEXT_DIM } from "@/constants/neon";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { API_ENDPOINTS, HTTP_METHODS, ROUTE_PATHS } from "@/constants/api";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { useCarouselProject } from "@/modules/editorial";
import { useEditorialWorkflow } from "@/modules/editorial";
import { AutoRepairButton } from "@/modules/editorial";
import {
  PublishPanel,
  PublishFailedNotice,
  RebuildPdfSection,
  RegenerateStrategySection,
  mergePublishProjectWithWorkflow,
  usePublishInstagram,
  useRepublishCarousel,
} from "@/modules/publishing";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

type PublishResult = {
  status: "idle" | "success" | "error";
  message?: string;
};

const panelStyle = {
  background: BG_CARD,
  border: "1px solid rgba(255,255,255,0.06)",
  borderRadius: "8px",
  padding: "20px",
};

export default function DashboardCreatePublishPage(): React.ReactElement {
  const params = useParams<{ id: string }>();
  const projectId = params.id;
  const t = useTranslations("publish");
  const {
    data: project,
    isLoading,
    refetch: refetchProject,
  } = useCarouselProject(projectId);
  const { refreshState, state: workflowState } =
    useEditorialWorkflow(projectId);
  const publishInstagram = usePublishInstagram();
  const republish = useRepublishCarousel();
  const [publishResult, setPublishResult] = useState<PublishResult>({
    status: "idle",
  });
  const [sitePublishMessage, setSitePublishMessage] = useState<string | null>(
    null,
  );
  // AE-0313: the freshly rebuilt artifact version, used to cache-bust the
  // served PDF/slide URLs after a "Rebuild PDF".
  const [rebuiltVersion, setRebuiltVersion] = useState<string | null>(null);

  const handleRebuilt = useCallback(
    (artifactVersion: string | null): void => {
      setRebuiltVersion(artifactVersion);
      void Promise.all([refreshState(), refetchProject()]);
    },
    [refreshState, refetchProject],
  );

  useEffect(() => {
    void refreshState();
  }, [refreshState]);

  useEffect(() => {
    if (workflowState?.caption && !project?.caption) {
      void refetchProject();
    }
  }, [workflowState?.caption, project?.caption, refetchProject]);

  const canPublishToSite =
    workflowState?.workflow_status ===
    EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH;

  const handlePublishToSite = useCallback(async (): Promise<void> => {
    setSitePublishMessage(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.CAROUSEL_PUBLISH(projectId),
        { method: HTTP_METHODS.POST },
      );
      if (!response.ok) {
        let detail = t("sitePublishFailed");
        try {
          const body = (await response.json()) as { detail?: string };
          if (typeof body.detail === "string" && body.detail.length > 0) {
            detail = body.detail;
          }
        } catch {
          // keep generic message
        }
        throw new Error(detail);
      }
      setSitePublishMessage(t("sitePublished"));
      await Promise.all([refreshState(), refetchProject()]);
    } catch (error) {
      setSitePublishMessage(
        error instanceof Error ? error.message : t("sitePublishFailed"),
      );
    }
  }, [projectId, t, refreshState, refetchProject]);

  const handlePublishInstagram = useCallback(
    async (caption: string) => {
      try {
        const result = await publishInstagram.mutateAsync({
          projectId,
          caption,
        });
        if (result.status === "failed") {
          setPublishResult({
            status: "error",
            message: result.error_message ?? t("instagram.failed"),
          });
          return;
        }
        setPublishResult({
          status: "success",
          message:
            result.status === "published"
              ? t("instagram.published")
              : t("instagram.queued"),
        });
      } catch (error) {
        setPublishResult({
          status: "error",
          message:
            error instanceof Error ? error.message : t("instagram.failed"),
        });
      }
    },
    [projectId, publishInstagram, t],
  );

  if (isLoading) {
    return (
      <div
        className="flex flex-1 items-center justify-center text-white"
        style={{ minHeight: "40vh" }}
      >
        <NeonSpinner />
      </div>
    );
  }

  if (!project) {
    return (
      <div className="flex flex-1 flex-col p-7 text-white">
        <NeonTopBar title="Publish" breadcrumb={[{ label: "project" }]} />
        <p className="mt-6 text-red-400">{t("notFound")}</p>
      </div>
    );
  }

  const publishProject = mergePublishProjectWithWorkflow(
    project,
    workflowState,
  );

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title="Publish"
        breadcrumb={[
          {
            label: project.topic,
            href: DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId),
          },
          { label: "publish" },
        ]}
      />

      <div className="w-full max-w-[960px] p-4 md:p-7">
        <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div>
            <h1 style={{ fontSize: "20px", fontWeight: 700, margin: 0 }}>
              {project.title || project.topic}
            </h1>
            <p style={{ fontSize: "13px", color: TEXT_DIM, marginTop: "6px" }}>
              {project.audience} · {project.niche}
            </p>
          </div>
          <Link
            href={`${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=publish`}
            className="inline-flex shrink-0 items-center [@media(pointer:coarse)]:min-h-11"
            style={{
              fontSize: "13px",
              color: "#00d4ff",
              textDecoration: "none",
            }}
          >
            {t("backToWorkspace")}
          </Link>
        </div>

        {!canPublishToSite &&
          workflowState?.phase_status === WORKFLOW_PHASE_STATUS.FAILED && (
            <PublishFailedNotice
              currentPhase={workflowState.current_phase}
              errorMessage={workflowState.error_message}
              workspaceHref={`${DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId)}?step=outline`}
            />
          )}
        {!canPublishToSite &&
          workflowState?.phase_status !== WORKFLOW_PHASE_STATUS.FAILED && (
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
          )}

        {canPublishToSite && (
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              alignItems: "center",
              gap: "12px",
              marginBottom: "16px",
            }}
          >
            <NeonButton size="sm" onClick={() => void handlePublishToSite()}>
              {t("publishToSite")}
            </NeonButton>
            {sitePublishMessage ? (
              <span style={{ fontSize: "13px", color: TEXT_DIM }}>
                {sitePublishMessage}{" "}
                <Link
                  href={ROUTE_PATHS.BLOG_POST(projectId)}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{ color: "#00d4ff" }}
                >
                  {t("sitePublishedLink")}
                </Link>
              </span>
            ) : null}
          </div>
        )}

        <div style={panelStyle}>
          <PublishPanel
            project={publishProject}
            onPublishInstagram={
              canPublishToSite ? handlePublishInstagram : undefined
            }
            isPublishingInstagram={publishInstagram.isPending}
            publishResult={publishResult}
            cacheBustToken={rebuiltVersion ?? undefined}
          />
        </div>

        <div style={{ marginTop: "16px" }}>
          <RebuildPdfSection projectId={projectId} onRebuilt={handleRebuilt} />
          {/* AE-0311: one-click deterministic repair; a completed carousel
              chains AE-0313's republish so the served PDF reflects the fix. */}
          <div style={{ marginTop: "12px" }}>
            <AutoRepairButton
              projectId={projectId}
              onRepaired={() => {
                void Promise.all([refreshState(), refetchProject()]);
              }}
              onRepublishNeeded={() => {
                republish.mutate(
                  { projectId },
                  {
                    onSuccess: (data) =>
                      handleRebuilt(data.artifact_version ?? null),
                  },
                );
              }}
            />
          </div>
        </div>

        <div style={{ marginTop: "16px" }}>
          <RegenerateStrategySection project={project} projectId={projectId} />
        </div>
      </div>
    </div>
  );
}
