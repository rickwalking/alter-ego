"use client";

import type { EditorialWorkflowState } from "@/modules/publishing";
import {
  CREATE_STEP_IDS,
  type CreateStepId,
} from "@/app/dashboard/create/step-ids";
import {
  ContentHistory,
  ImagesHistory,
  OutlineHistory,
  PublishHistory,
  ResearchHistory,
  ReviewHistory,
  StepHistoryEmpty,
  type StepHistorySectionProps,
} from "./create-step-history-sections";

interface CreateStepHistoryPanelProps {
  viewStepId: CreateStepId;
  state: EditorialWorkflowState;
}

/** The read-only view of each step that has one. */
const STEP_HISTORY_SECTIONS: Partial<
  Record<CreateStepId, (props: StepHistorySectionProps) => React.JSX.Element>
> = {
  [CREATE_STEP_IDS.RESEARCH]: ResearchHistory,
  [CREATE_STEP_IDS.OUTLINE]: OutlineHistory,
  [CREATE_STEP_IDS.CONTENT]: ContentHistory,
  [CREATE_STEP_IDS.IMAGES]: ImagesHistory,
  [CREATE_STEP_IDS.REVIEW]: ReviewHistory,
  [CREATE_STEP_IDS.PUBLISH]: PublishHistory,
};

export function CreateStepHistoryPanel({
  viewStepId,
  state,
}: CreateStepHistoryPanelProps): React.JSX.Element {
  const Section = STEP_HISTORY_SECTIONS[viewStepId] ?? StepHistoryEmpty;
  return <Section state={state} />;
}
