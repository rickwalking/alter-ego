// AE-0414 — Gherkin: frontend/tests/features/content-review-manual-fixes-ae0414.feature
import { describe, expect, it } from "vitest";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
} from "@/modules/editorial/workspace/types-ai";
import {
  applySlideExtraEdit,
  applySlideStructuredItemEdit,
  changedLocalizedSlides,
  resolveLocalizedSlides,
  slidesHaveCopyChanges,
} from "./presentation-slide-resolution";

const LONG_BODY = `${"palavra ".repeat(37)}fim.`; // 300 characters

function localized(index: number, heading: string): LocalizedSlideReview {
  return {
    slide_index: index,
    slide_type: "content",
    presentation_pt: { slide_type: "content", heading, body: `Corpo ${index}` },
    presentation_en: { slide_type: "content", heading, body: `Body ${index}` },
  };
}

function draft(
  index: number,
  withPresentation: boolean,
): Record<string, unknown> {
  const base = {
    slide_index: index,
    slide_type: "content",
    title: `Draft ${index}`,
  };
  if (!withPresentation) {
    return base;
  }
  return {
    ...base,
    presentation_pt: { heading: `Rascunho ${index}`, body: "PT draft" },
    presentation_en: { heading: `Draft ${index}`, body: "EN draft" },
  };
}

function stateWith(
  localizedSlides: LocalizedSlideReview[] | undefined,
  drafts: Record<string, unknown>[],
): EditorialWorkflowState {
  return {
    project_id: "p1",
    current_phase: EDITORIAL_PHASES.CONTENT,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: drafts,
    status: "draft",
    localized_slides: localizedSlides,
  };
}

describe("resolveLocalizedSlides (AE-0414 B10)", () => {
  // Scenario: Every slide renders even when some drafts lack presentations
  it("keeps every slide when only some drafts carry presentations", () => {
    const indexes = [1, 2, 3, 4, 5, 6, 7];
    const state = stateWith(
      indexes.map((index) => localized(index, `Heading ${index}`)),
      indexes.map((index) => draft(index, [1, 2, 6, 7].includes(index))),
    );

    const slides = resolveLocalizedSlides(state);

    expect(slides.map((slide) => slide.slide_index)).toEqual(indexes);
  });

  // Scenario: The validated localized copy wins over the draft copy of the same slide
  it("prefers the localized copy of a slide over its draft presentation", () => {
    const state = stateWith([localized(2, "Validated")], [draft(2, true)]);

    const [slide] = resolveLocalizedSlides(state);

    expect(slide.presentation_pt.heading).toBe("Validated");
    expect(slide.presentation_en.body).toBe("Body 2");
  });

  // Scenario: A malformed localized slide falls back to its draft presentation
  it("falls back to the draft presentation for a malformed localized slide", () => {
    const malformed: LocalizedSlideReview = {
      ...localized(1, ""),
      presentation_pt: { heading: "", body: "{'pt': {'heading': 'x'}}" },
    };
    const state = stateWith([malformed, localized(2, "Ok")], [draft(1, true)]);

    const slides = resolveLocalizedSlides(state);

    expect(slides[0].presentation_pt.heading).toBe("Rascunho 1");
    expect(slides[1].presentation_pt.heading).toBe("Ok");
  });

  it("still shows a malformed localized slide that has no draft", () => {
    const malformed: LocalizedSlideReview = {
      ...localized(4, ""),
      presentation_pt: { heading: "", body: "{raw}" },
    };

    const slides = resolveLocalizedSlides(stateWith([malformed], []));

    expect(slides).toHaveLength(1);
    expect(slides[0].slide_index).toBe(4);
  });

  it("adds slides that exist only as drafts, in slide order", () => {
    const state = stateWith(
      [localized(3, "Three")],
      [draft(1, false), draft(2, true), draft(3, true)],
    );

    const slides = resolveLocalizedSlides(state);

    expect(slides.map((slide) => slide.slide_index)).toEqual([1, 2, 3]);
    expect(slides[0].presentation_pt.heading).toBe("Draft 1");
    expect(slides[1].presentation_en.heading).toBe("Draft 2");
    expect(slides[2].presentation_pt.heading).toBe("Three");
  });

  it("numbers drafts without a slide_index by position and reads legacy copy", () => {
    const state = stateWith(undefined, [
      { type: "intro", heading: "Hook", body: "Sub" },
      { draft_text: "Only text" },
    ]);

    const slides = resolveLocalizedSlides(state);

    expect(slides.map((slide) => slide.slide_index)).toEqual([1, 2]);
    expect(slides[0].slide_type).toBe("intro");
    expect(slides[0].presentation_en).toEqual({
      slide_type: "intro",
      heading: "Hook",
      body: "Sub",
    });
    expect(slides[1].slide_type).toBe("content");
    expect(slides[1].presentation_pt.body).toBe("Only text");
  });
});

describe("manual-fix payload (AE-0414 B04/B11)", () => {
  // Scenario: Manual fixes send only the changed slides, verbatim
  it("returns only the changed slides, with untouched copy verbatim", () => {
    const first: LocalizedSlideReview = {
      ...localized(1, "Um"),
      presentation_pt: { heading: "Um", body: LONG_BODY },
    };
    const baseline = [first, localized(2, "Dois")];
    const edited = baseline.map((slide) =>
      slide.slide_index === 1
        ? {
            ...slide,
            presentation_en: { ...slide.presentation_en, heading: "One" },
          }
        : slide,
    );

    const changed = changedLocalizedSlides(baseline, edited);

    expect(changed).toHaveLength(1);
    expect(changed[0].slide_index).toBe(1);
    expect(changed[0].presentation_pt.body).toBe(LONG_BODY);
    expect(String(changed[0].presentation_pt.body)).toHaveLength(300);
    expect(changed[0].presentation_en.heading).toBe("One");
  });

  it("returns nothing when nothing changed", () => {
    const baseline = [localized(1, "Um")];
    expect(changedLocalizedSlides(baseline, [...baseline])).toEqual([]);
  });

  // Scenario: A flagged summary point is editable in both locales
  it("counts a structured item edit as a copy change", () => {
    const slide: LocalizedSlideReview = {
      ...localized(2, "Resumo"),
      presentation_en: {
        heading: "Summary",
        summary_points: [{ title: "A", body: "old" }],
      },
    };
    const edited = applySlideStructuredItemEdit([slide], {
      slideIndex: 2,
      locale: "presentation_en",
      listKey: "summary_points",
      itemIndex: 0,
      field: "body",
      value: "new",
    });

    expect(slidesHaveCopyChanges([slide], edited)).toBe(true);
    expect(changedLocalizedSlides([slide], edited)[0].presentation_en).toEqual({
      heading: "Summary",
      summary_points: [{ title: "A", body: "new" }],
    });
  });

  it("detects reordered or resized slide lists as changes", () => {
    const baseline = [localized(1, "A"), localized(2, "B")];
    expect(slidesHaveCopyChanges(baseline, [baseline[0]])).toBe(true);
    expect(slidesHaveCopyChanges(baseline, [baseline[1], baseline[0]])).toBe(
      true,
    );
    expect(slidesHaveCopyChanges(baseline, [...baseline])).toBe(false);
  });
});

describe("applySlideExtraEdit (AE-0414 B11)", () => {
  const cta: LocalizedSlideReview = {
    slide_index: 7,
    slide_type: "cta",
    presentation_pt: {
      creator_name: "Pedro",
      insight: { icon_name: "quote", quote: "Q", attribution: "A" },
      stats: [1],
    },
    presentation_en: { creator_name: "Pedro" },
  };

  it("replaces a string extra", () => {
    const [edited] = applySlideExtraEdit([cta], {
      slideIndex: 7,
      locale: "presentation_pt",
      extraKey: "creator_name",
      value: "Pedro Marins",
    });
    expect(edited.presentation_pt.creator_name).toBe("Pedro Marins");
    expect(edited.presentation_en.creator_name).toBe("Pedro");
  });

  it("edits one text field of an object extra, keeping the rest", () => {
    const [edited] = applySlideExtraEdit([cta], {
      slideIndex: 7,
      locale: "presentation_pt",
      extraKey: "insight",
      field: "quote",
      value: "New quote",
    });
    expect(edited.presentation_pt.insight).toEqual({
      icon_name: "quote",
      quote: "New quote",
      attribution: "A",
    });
  });

  it("leaves a non-object extra and other slides alone", () => {
    const other = localized(1, "Um");
    const [untouched, edited] = applySlideExtraEdit([other, cta], {
      slideIndex: 7,
      locale: "presentation_pt",
      extraKey: "stats",
      field: "title",
      value: "x",
    });
    expect(untouched).toBe(other);
    expect(edited.presentation_pt.stats).toEqual([1]);
  });
});
