"use client";

import { useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import {
  PublishPanel,
  mergePublishProjectWithWorkflow,
} from "@/modules/publishing";
import { isPublishReady } from "@/app/dashboard/create/[id]/publish/publish-readiness";
import {
  useInstagramPublish,
  usePublishPageData,
  usePublishToSite,
} from "./use-publish-page";
import {
  PublishNotReady,
  PublishPageHeading,
  PublishStatusNotices,
  SitePublishBar,
  panelStyle,
} from "./publish-page-sections";
import { PublishArtifactTools } from "./publish-artifact-tools";

function PublishPageLoading(): React.ReactElement {
  return (
    <div
      className="flex flex-1 items-center justify-center text-white"
      style={{ minHeight: "40vh" }}
    >
      <NeonSpinner />
    </div>
  );
}

function PublishPageNotFound(): React.ReactElement {
  const t = useTranslations("publish");
  const tCreate = useTranslations("create");
  return (
    <div className="flex flex-1 flex-col p-7 text-white">
      <NeonTopBar
        title={t("pageTitle")}
        breadcrumb={[{ label: tCreate("topBar.project") }]}
      />
      <p className="mt-6 text-red-400">{t("notFound")}</p>
    </div>
  );
}

export default function DashboardCreatePublishPage(): React.ReactElement {
  const t = useTranslations("publish");
  const data = usePublishPageData();
  const { projectId, projectQuery, workflowState } = data;
  const site = usePublishToSite(projectId, data.refreshAll);
  const instagram = useInstagramPublish(projectId);
  const project = projectQuery.data;

  if (projectQuery.isLoading || (project && !data.workflowLoaded)) {
    return <PublishPageLoading />;
  }
  if (!project) {
    return <PublishPageNotFound />;
  }

  const { canPublishToSite, localizedSlides } = data;
  const artifactsReady = isPublishReady(project, workflowState);

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title={t("pageTitle")}
        breadcrumb={[
          {
            label: project.topic,
            href: DASHBOARD_ROUTES.CREATE_WORKSPACE(projectId),
          },
          { label: t("breadcrumb") },
        ]}
      />

      <div className="w-full max-w-[960px] p-4 md:p-7">
        <PublishPageHeading project={project} projectId={projectId} />
        <PublishStatusNotices
          workflowState={workflowState}
          projectId={projectId}
          canPublishToSite={canPublishToSite}
          artifactsReady={artifactsReady}
        />
        {canPublishToSite && (
          <SitePublishBar
            publishedHref={site.publishedHref}
            message={site.sitePublishMessage}
            onPublish={site.handlePublishToSite}
          />
        )}
        <PublishNotReady
          workflowState={workflowState}
          artifactsReady={artifactsReady}
        />

        {artifactsReady && (
          <>
            <div style={panelStyle}>
              <PublishPanel
                project={mergePublishProjectWithWorkflow(
                  project,
                  workflowState,
                )}
                onPublishInstagram={
                  canPublishToSite
                    ? instagram.handlePublishInstagram
                    : undefined
                }
                isPublishingInstagram={instagram.isPublishing}
                publishResult={instagram.publishResult}
                cacheBustToken={data.rebuiltVersion ?? undefined}
                slideNumbers={localizedSlides.map((slide) => slide.slide_index)}
              />
            </div>
            <PublishArtifactTools
              data={data}
              project={project}
              localizedSlides={localizedSlides}
            />
          </>
        )}
      </div>
    </div>
  );
}
