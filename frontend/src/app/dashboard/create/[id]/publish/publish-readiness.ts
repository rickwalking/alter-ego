import {
  EDITORIAL_PHASES,
  EDITORIAL_WORKFLOW_STATUS,
} from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/publishing";
import type { CarouselProjectResponse } from "@/schemas/carousel";

const READY_PHASES: ReadonlySet<string> = new Set([
  EDITORIAL_PHASES.FINAL_REVIEW,
  EDITORIAL_PHASES.PUBLISHED,
]);

const RADAR_CONTENT_MODE = "news_analysis";

/**
 * The publish artifacts (PDF, slide images) and the actions that
 * rebuild or edit them exist only once the workflow reached the final review
 * (or was approved). A project with no editorial workflow state (legacy
 * pipeline) is ready when it has a PDF.
 */
export function isPublishReady(
  project: Pick<CarouselProjectResponse, "pdf_path">,
  workflow: EditorialWorkflowState | null,
): boolean {
  if (!workflow) {
    return Boolean(project.pdf_path);
  }
  return (
    workflow.workflow_status ===
      EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH ||
    READY_PHASES.has(workflow.current_phase)
  );
}

/**
 * "Publicar agora" on Instagram is offered once the carousel is approved for
 * publish, and while it waits for the owner's final review: the backend then
 * approves the final review before it posts, as the Telegram button does.
 */
export function canPublishInstagram(
  workflow: EditorialWorkflowState | null | undefined,
): boolean {
  if (!workflow) {
    return false;
  }
  if (
    workflow.workflow_status === EDITORIAL_WORKFLOW_STATUS.APPROVED_FOR_PUBLISH
  ) {
    return true;
  }
  return (
    workflow.current_phase === EDITORIAL_PHASES.FINAL_REVIEW &&
    workflow.phase_status === WORKFLOW_PHASE_STATUS.AWAITING_HUMAN
  );
}

/** The Radar IA layout templates only fit Radar IA projects. */
export function offersRadarTemplates(
  project: Pick<CarouselProjectResponse, "content_mode">,
): boolean {
  return (project.content_mode ?? RADAR_CONTENT_MODE) === RADAR_CONTENT_MODE;
}

/** The slide-1 cover picker belongs to Ponto de Vista projects only. */
export function offersCoverPicker(
  project: Pick<CarouselProjectResponse, "content_mode">,
): boolean {
  return !offersRadarTemplates(project);
}
