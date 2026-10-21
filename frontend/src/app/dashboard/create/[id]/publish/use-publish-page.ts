"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { EDITORIAL_WORKFLOW_STATUS } from "@/constants/editorial-workflow";
import {
  resolveLocalizedSlides,
  useCarouselProject,
  useEditorialWorkflow,
} from "@/modules/editorial";
import {
  usePublishInstagram,
  useRepublishCarousel,
  type LocalizedSlideReview,
} from "@/modules/publishing";
import { authenticatedFetch } from "@/lib/authenticated-fetch";

export interface PublishResult {
  status: "idle" | "success" | "error";
  message?: string;
}

type CarouselProjectQuery = ReturnType<typeof useCarouselProject>;
type EditorialWorkflow = ReturnType<typeof useEditorialWorkflow>;

export type LoadedProject = NonNullable<CarouselProjectQuery["data"]>;

/** The project and workflow the publish page shows, and their refresh. */
export interface PublishPageData {
  projectId: string;
  projectQuery: CarouselProjectQuery;
  workflowState: EditorialWorkflow["state"];
  workflowLoaded: boolean;
  /** Refetch the workflow state and the project together. */
  refreshAll: () => Promise<unknown>;
  /** The rebuilt artifact version that cache-busts served URLs. */
  rebuiltVersion: string | null;
  handleRebuilt: (artifactVersion: string | null) => void;
  /** Republish after a repair, then cache-bust. */
  republishAfterRepair: () => void;
  /** Approved for publish: the site and Instagram publishes are offered. */
  canPublishToSite: boolean;
  localizedSlides: LocalizedSlideReview[];
}

/** Republish the carousel, then cache-bust with the new artifact version. */
function useRepublishAfterRepair(
  projectId: string,
  onRebuilt: (artifactVersion: string | null) => void,
): () => void {
  const republish = useRepublishCarousel();
  return (): void => {
    republish.mutate(
      { projectId },
      { onSuccess: (data) => onRebuilt(data.artifact_version ?? null) },
    );
  };
}

/** The workflow wrote a caption the loaded project lacks: refetch it. */
function useRefetchForNewCaption(
  workflowCaption: string | null | undefined,
  projectCaption: string | null | undefined,
  refetchProject: () => Promise<unknown>,
): void {
  useEffect(() => {
    if (workflowCaption && !projectCaption) {
      void refetchProject();
    }
  }, [workflowCaption, projectCaption, refetchProject]);
}

/**
 * The workflow state is not fetched on mount: the page refreshes it itself and
 * waits for it before deciding whether the artifacts exist.
 */
export function usePublishPageData(): PublishPageData {
  const projectId = useParams<{ id: string }>().id;
  const projectQuery = useCarouselProject(projectId);
  const { refetch: refetchProject } = projectQuery;
  const { refreshState, state: workflowState } = useEditorialWorkflow(
    projectId,
    { initialFetch: false },
  );
  const [workflowLoaded, setWorkflowLoaded] = useState(false);
  const [rebuiltVersion, setRebuiltVersion] = useState<string | null>(null);

  const refreshAll = useCallback(
    (): Promise<unknown> => Promise.all([refreshState(), refetchProject()]),
    [refreshState, refetchProject],
  );

  const handleRebuilt = useCallback(
    (artifactVersion: string | null): void => {
      setRebuiltVersion(artifactVersion);
      void refreshAll();
    },
    [refreshAll],
  );

  useEffect(() => {
    void refreshState().then(() => setWorkflowLoaded(true));
  }, [refreshState]);

  useRefetchForNewCaption(
    workflowState?.caption,
    projectQuery.data?.caption,
    refetchProject,
  );

  const republishAfterRepair = useRepublishAfterRepair(
    projectId,
    handleRebuilt,
  );

  return {
    projectId,
    projectQuery,
    workflowState,
    workflowLoaded,
    refreshAll,
    rebuiltVersion,
    handleRebuilt,
    republishAfterRepair,
    canPublishToSite:
      workflowState?.workflow_status ===
      EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH,
    localizedSlides: workflowState ? resolveLocalizedSlides(workflowState) : [],
  };
}

/** The error detail of a failed site publish (generic when unreadable). */
async function sitePublishError(
  response: Response,
  fallback: string,
): Promise<string> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string" && body.detail.length > 0) {
      return body.detail;
    }
  } catch {}
  return fallback;
}

/** Publish the approved carousel to the public site. */
export function usePublishToSite(
  projectId: string,
  refreshAll: () => Promise<unknown>,
): { sitePublishMessage: string | null; handlePublishToSite: () => void } {
  const t = useTranslations("publish");
  const [sitePublishMessage, setSitePublishMessage] = useState<string | null>(
    null,
  );
  const publish = async (): Promise<void> => {
    setSitePublishMessage(null);
    try {
      const response = await authenticatedFetch(
        API_ENDPOINTS.CAROUSEL_PUBLISH(projectId),
        { method: HTTP_METHODS.POST },
      );
      if (!response.ok) {
        throw new Error(
          await sitePublishError(response, t("sitePublishFailed")),
        );
      }
      setSitePublishMessage(t("sitePublished"));
      await refreshAll();
    } catch (error) {
      setSitePublishMessage(
        error instanceof Error ? error.message : t("sitePublishFailed"),
      );
    }
  };
  return {
    sitePublishMessage,
    handlePublishToSite: () => {
      void publish();
    },
  };
}

/** Publish (or queue) the carousel on Instagram and report the outcome. */
export function useInstagramPublish(projectId: string): {
  publishResult: PublishResult;
  isPublishing: boolean;
  handlePublishInstagram: (caption: string) => Promise<void>;
} {
  const t = useTranslations("publish");
  const publishInstagram = usePublishInstagram();
  const [publishResult, setPublishResult] = useState<PublishResult>({
    status: "idle",
  });
  const handlePublishInstagram = async (caption: string): Promise<void> => {
    try {
      const result = await publishInstagram.mutateAsync({ projectId, caption });
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
        message: error instanceof Error ? error.message : t("instagram.failed"),
      });
    }
  };
  return {
    publishResult,
    isPublishing: publishInstagram.isPending,
    handlePublishInstagram,
  };
}
