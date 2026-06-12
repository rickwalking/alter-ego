import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";

export const CREATE_STEPS = [
  { num: 1, id: CREATE_STEP_IDS.BRIEF, label: "Brief" },
  { num: 2, id: CREATE_STEP_IDS.RESEARCH, label: "Research" },
  { num: 3, id: CREATE_STEP_IDS.OUTLINE, label: "Outline" },
  { num: 4, id: CREATE_STEP_IDS.CONTENT, label: "Content" },
  { num: 5, id: CREATE_STEP_IDS.IMAGES, label: "Images" },
  { num: 6, id: CREATE_STEP_IDS.REVIEW, label: "Review" },
  { num: 7, id: CREATE_STEP_IDS.PUBLISH, label: "Publish" },
] as const;

export { CREATE_TEMPLATES } from "@/constants/create";
export type { CreateTemplate } from "@/constants/create";
