import { describe, it, expect } from "vitest";
import { mergePublishProjectWithWorkflow } from "./merge-publish-project";
import type { CarouselProjectResponse } from "@/schemas/carousel";

const baseProject = {
  id: "proj-1",
  topic: "Topic",
  audience: "Devs",
  niche: "Tech",
  status: "completed",
  caption: null,
  linkedin_post_pt: null,
  linkedin_post_en: null,
} as CarouselProjectResponse;

describe("mergePublishProjectWithWorkflow", () => {
  it("fills caption and LinkedIn from workflow when project fields are empty", () => {
    const merged = mergePublishProjectWithWorkflow(baseProject, {
      project_id: "proj-1",
      current_phase: "final_review",
      phase_status: "awaiting_human",
      research_findings: [],
      outline: [],
      slide_drafts: [],
      status: "draft",
      caption: "Instagram caption",
      linkedin_post_pt: "LinkedIn PT",
      linkedin_post_en: "LinkedIn EN",
    });
    expect(merged.caption).toBe("Instagram caption");
    expect(merged.linkedin_post_pt).toBe("LinkedIn PT");
    expect(merged.linkedin_post_en).toBe("LinkedIn EN");
  });

  it("keeps project fields when already set", () => {
    const merged = mergePublishProjectWithWorkflow(
      {
        ...baseProject,
        caption: "From DB",
        linkedin_post_pt: "DB PT",
      },
      {
        project_id: "proj-1",
        current_phase: "final_review",
        phase_status: "approved",
        research_findings: [],
        outline: [],
        slide_drafts: [],
        status: "draft",
        caption: "From workflow",
        linkedin_post_pt: "WF PT",
      },
    );
    expect(merged.caption).toBe("From DB");
    expect(merged.linkedin_post_pt).toBe("DB PT");
  });
});
