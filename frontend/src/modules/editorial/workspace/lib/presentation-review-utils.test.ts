import { describe, expect, it } from "vitest";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type { EditorialWorkflowState } from "@/modules/editorial";
import type { LocalizedSlideReview } from "@/modules/editorial";
import {
  formatBudgetUsage,
  hasBlockingPresentationViolations,
  isBudgetExceeded,
  isWarningViolation,
  listPresentationIconNames,
  listPresentationStructuredItems,
  listPresentationViolations,
  listStructuredExtras,
  localizedSlidesHaveBudgetViolations,
  resolvePresentationPreviewText,
  resolveBodyBudget,
  resolveHeadingBudget,
  violationToneClasses,
} from "./presentation-review-utils";
import {
  applySlideCopyEdit,
  resolveLocalizedSlides,
  slidesHaveCopyChanges,
} from "./presentation-slide-resolution";

const baseState: EditorialWorkflowState = {
  project_id: "project-1",
  current_phase: EDITORIAL_PHASES.CONTENT,
  phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
  research_findings: [],
  outline: [],
  slide_drafts: [],
  status: "draft",
};

describe("presentation review utils", () => {
  // Feature: Versioned carousel presentation contract
  // Scenario: Invalid copy remains invalid after repair and blocks approval
  it("detects blocking presentation violations", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      presentation_validation: {
        validation_status: "invalid",
        validated_at: "2026-06-09T00:00:00.000Z",
        blocking: true,
        violations: [
          {
            code: "visible_emoji_forbidden",
            message: "Visible text must not contain decorative emoji",
            slide_index: 1,
            locale: "pt",
            field: "heading",
          },
        ],
      },
    };

    expect(hasBlockingPresentationViolations(state)).toBe(true);
    expect(listPresentationViolations(state)).toHaveLength(1);
  });

  it("prefers structured presentation fields on slide drafts over malformed localized slides", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      localized_slides: [
        {
          slide_index: 1,
          slide_type: "intro",
          presentation_pt: {
            slide_type: "intro",
            heading: "",
            body: "{'pt': {'heading': 'Bad'}}",
          },
          presentation_en: {
            slide_type: "intro",
            heading: "slide",
            body: "bad",
          },
        },
      ],
      slide_drafts: [
        {
          slide_index: 1,
          slide_type: "intro",
          presentation_pt: {
            slide_type: "intro",
            heading: "Good PT",
            body: "Subtitle PT",
          },
          presentation_en: {
            slide_type: "intro",
            heading: "Good EN",
            body: "Subtitle EN",
          },
        },
      ],
    };

    const localized = resolveLocalizedSlides(state);

    expect(localized[0]?.presentation_pt.heading).toBe("Good PT");
    expect(localized[0]?.presentation_en.heading).toBe("Good EN");
  });

  it("falls back to slide drafts when localized slides are absent", () => {
    const state: EditorialWorkflowState = {
      ...baseState,
      slide_drafts: [
        {
          slide_index: 1,
          slide_type: "intro",
          title: "Hook",
          draft_text: "Subtitle",
        },
      ],
    };

    const localized = resolveLocalizedSlides(state);

    expect(localized).toHaveLength(1);
    expect(localized[0]?.presentation_pt.heading).toBe("Hook");
    expect(localized[0]?.presentation_pt.body).toBe("Subtitle");
  });

  it("lists structured extras and icon names from union payloads", () => {
    const presentation = {
      slide_type: "content",
      heading: "Title",
      body: "Body",
      features: [{ icon_name: "brain", title: "Signal", body: "Detail" }],
    };

    expect(listStructuredExtras(presentation)).toEqual([]);
    expect(listPresentationStructuredItems(presentation)).toEqual(
      presentation.features,
    );
    expect(listPresentationIconNames(presentation)).toEqual(["brain"]);
  });

  it("builds preview text from body and structured items", () => {
    const presentation = {
      slide_type: "summary",
      heading: "Summary",
      body: "",
      summary_points: [
        {
          icon_name: "book-open",
          title: "Origin",
          body: "Where the term comes from.",
        },
      ],
    };

    expect(resolvePresentationPreviewText(presentation)).toBe(
      "• Origin: Where the term comes from.",
    );
  });

  it("formats heading budget usage for hero_lower_third_v1", () => {
    const budget = resolveHeadingBudget("intro", "hero_lower_third_v1");
    const usage = formatBudgetUsage("Hook", budget);

    expect(usage).toBe("4/72 chars · 1/3 lines");
  });

  it("applies slide copy edits by slide index and locale", () => {
    const slides: LocalizedSlideReview[] = [
      {
        slide_index: 1,
        slide_type: "intro",
        presentation_pt: {
          slide_type: "intro",
          heading: "Antigo",
          body: "Corpo",
        },
        presentation_en: { slide_type: "intro", heading: "Old", body: "Body" },
      },
    ];

    const edited = applySlideCopyEdit(slides, {
      slideIndex: 1,
      locale: "presentation_pt",
      field: "heading",
      value: "Novo",
    });

    expect(edited[0]?.presentation_pt.heading).toBe("Novo");
    expect(edited[0]?.presentation_en.heading).toBe("Old");
  });

  it("detects copy changes between baseline and edited slides", () => {
    const baseline: LocalizedSlideReview[] = [
      {
        slide_index: 1,
        slide_type: "intro",
        presentation_pt: { slide_type: "intro", heading: "A", body: "B" },
        presentation_en: { slide_type: "intro", heading: "A", body: "B" },
      },
    ];
    const unchanged = applySlideCopyEdit(baseline, {
      slideIndex: 1,
      locale: "presentation_pt",
      field: "heading",
      value: "A",
    });

    expect(slidesHaveCopyChanges(baseline, unchanged)).toBe(false);
    expect(
      slidesHaveCopyChanges(
        baseline,
        applySlideCopyEdit(baseline, {
          slideIndex: 1,
          locale: "presentation_en",
          field: "body",
          value: "Changed",
        }),
      ),
    ).toBe(true);
  });

  it("does not apply website budget to cta body copy", () => {
    const slides: LocalizedSlideReview[] = [
      {
        slide_index: 7,
        slide_type: "cta",
        presentation_pt: {
          slide_type: "cta",
          heading: "Fique por dentro",
          body: "Salve este carrossel e siga o perfil para acompanhar as novidades sobre modelos de IA avançados.",
          creator_website: "ia-avancada.com.br",
        },
        presentation_en: {
          slide_type: "cta",
          heading: "Stay in the loop",
          body: "Save this carousel and follow the profile to keep up with the latest on advanced AI models.",
          creator_website: "ia-avancada.com.br",
        },
      },
    ];

    expect(resolveBodyBudget("cta", "hero_lower_third_v1")).toBeNull();
    expect(
      localizedSlidesHaveBudgetViolations(slides, "hero_lower_third_v1"),
    ).toBe(false);
  });

  it("flags budget violations in edited localized slides", () => {
    const budget = resolveHeadingBudget("intro", "hero_lower_third_v1");
    const oversized = "X".repeat((budget?.maxCharacters ?? 0) + 1);
    const slides: LocalizedSlideReview[] = [
      {
        slide_index: 1,
        slide_type: "intro",
        presentation_pt: { slide_type: "intro", heading: oversized, body: "" },
        presentation_en: { slide_type: "intro", heading: "OK", body: "" },
      },
    ];

    expect(isBudgetExceeded(oversized, budget)).toBe(true);
    expect(
      localizedSlidesHaveBudgetViolations(slides, "hero_lower_third_v1"),
    ).toBe(true);
  });
});

// AE-0312: warning-tier violations render distinctly from blockers.
// Feature: tests/features/carousel_pt_casing_severity.feature
describe("violation severity styling (AE-0312)", () => {
  it("classifies warning-severity casing violations as warnings", () => {
    expect(
      isWarningViolation({
        code: "heading_not_sentence_case_pt",
        message: "warn",
        severity: "warning",
      }),
    ).toBe(true);
  });

  it("treats a blocker and an absent severity as non-warning", () => {
    expect(
      isWarningViolation({
        code: "heading_empty",
        message: "x",
        severity: "blocker",
      }),
    ).toBe(false);
    expect(isWarningViolation({ code: "heading_empty", message: "x" })).toBe(
      false,
    );
  });

  it("gives warnings and blockers distinct tone classes", () => {
    const warning = violationToneClasses({
      code: "proper_noun_casing",
      message: "w",
      severity: "warning",
    });
    const blocker = violationToneClasses({
      code: "heading_empty",
      message: "b",
    });

    expect(warning).not.toBe(blocker);
    expect(blocker).toContain("destructive");
    expect(warning).not.toContain("destructive");
  });
});
