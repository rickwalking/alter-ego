import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";

export const CREATE_STEPS = [
  { num: 1, id: CREATE_STEP_IDS.BRIEF },
  { num: 2, id: CREATE_STEP_IDS.RESEARCH },
  { num: 3, id: CREATE_STEP_IDS.OUTLINE },
  { num: 4, id: CREATE_STEP_IDS.CONTENT },
  { num: 5, id: CREATE_STEP_IDS.IMAGES },
  { num: 6, id: CREATE_STEP_IDS.REVIEW },
  { num: 7, id: CREATE_STEP_IDS.PUBLISH },
] as const;

export { CREATE_TEMPLATES } from "@/constants/create";
export type { CreateTemplate } from "@/constants/create";
