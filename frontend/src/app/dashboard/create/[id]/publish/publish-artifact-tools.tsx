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

/** Cover, rebuild/repair, slide text edits, blog draft and radar templates. */
export function PublishArtifactTools({
  data,
  project,
  localizedSlides,
}: {
  data: PublishPageData;
  project: LoadedProject;
  localizedSlides: LocalizedSlideReview[];
}): React.ReactElement {
  const { projectId, workflowState, handleRebuilt, refreshAll } = data;
  return (
    <>
      {/* AE-0445: swap slide 1's photo of a Ponto de Vista carousel. */}
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
        {/* AE-0311: one-click deterministic repair; a completed carousel
          chains AE-0313's republish so the served PDF reflects the fix. */}
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
          {/* AE-0314: fix slide text after completion without regenerating
            images; chains the republish so the served PDF reflects the edit. */}
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

      {/* AE-0425: the blog post is written from this carousel, as a draft. */}
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
