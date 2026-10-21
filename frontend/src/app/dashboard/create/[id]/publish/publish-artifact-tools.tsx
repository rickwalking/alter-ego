"use client";

import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import { AutoRepairButton } from "@/modules/editorial";
import {
  CoverPickerSection,
  CreateBlogFromCarousel,
  RebuildPdfSection,
  RegenerateStrategySection,
  SlideTextEditSection,
} from "@/modules/publishing";
import type { LocalizedSlideReview } from "@/modules/publishing";

import {
  offersCoverPicker,
  offersRadarTemplates,
} from "@/app/dashboard/create/[id]/publish/publish-readiness";
import type { LoadedProject, PublishPageData } from "./use-publish-page";
import { panelStyle } from "./publish-page-sections";

/**
 * Cover, rebuild/repair, slide text edits, blog draft and radar templates.
 *
 * Offers the slide-1 photo swap of a Ponto de Vista carousel, the one-click
 * deterministic repair and the post-completion slide text fix (which does not
 * regenerate images); repair and text fix chain the republish of a completed
 * carousel so the served PDF reflects them. The blog post is written from this
 * carousel, as a draft.
 */
export function PublishArtifactTools({
  data,
  project,
  localizedSlides,
}: Readonly<{
  data: PublishPageData;
  project: LoadedProject;
  localizedSlides: LocalizedSlideReview[];
}>): React.ReactElement {
  const { projectId, workflowState, handleRebuilt, refreshAll } = data;
  return (
    <>
      {workflowState && offersCoverPicker(project) && (
        <div style={{ marginTop: "16px" }}>
          <CoverPickerSection
            projectId={projectId}
            onSwitched={handleRebuilt}
          />
        </div>
      )}

      <div style={{ marginTop: "16px" }}>
        <RebuildPdfSection projectId={projectId} onRebuilt={handleRebuilt} />
        <div style={{ marginTop: "12px" }}>
          <AutoRepairButton
            projectId={projectId}
            onRepaired={() => {
              void refreshAll();
            }}
            onRepublishNeeded={data.republishAfterRepair}
          />
        </div>
      </div>

      {workflowState && (
        <div style={{ marginTop: "16px" }}>
          <SlideTextEditSection
            projectId={projectId}
            slides={localizedSlides}
            policyVersion={workflowState.presentation_policy_version}
            runInProgress={
              workflowState.phase_status === WORKFLOW_PHASE_STATUS.IN_PROGRESS
            }
            rebuildPending={Boolean(project.needs_republish_since)}
            onEdited={() => {
              void refreshAll();
            }}
          />
        </div>
      )}

      <div style={{ ...panelStyle, marginTop: "16px" }}>
        <CreateBlogFromCarousel
          projectId={projectId}
          isPublic={Boolean(project.is_public)}
        />
      </div>

      {offersRadarTemplates(project) && (
        <div style={{ marginTop: "16px" }}>
          <RegenerateStrategySection project={project} projectId={projectId} />
        </div>
      )}
    </>
  );
}
