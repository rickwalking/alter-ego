// AE-0430 — Gherkin: frontend/tests/features/content-review-en-structure-ae0430.feature
import { describe, expect, it } from "vitest";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import {
  mirrorLocaleStructure,
  otherLocaleKey,
} from "./presentation-locale-mirror";
import {
  applySlideExtraEdit,
  applySlideStructuredItemEdit,
  changedLocalizedSlides,
} from "./presentation-slide-resolution";

const TLDR_PT = "Grok Bot, reserva por telefone, agente com computador próprio";
const ACTIONS_PT = [
  { icon_name: "target", title: "Escolha uma tarefa", body: "Um comando." },
  { icon_name: "eye", title: "Acompanhe", body: "Leia cada passo." },
  { icon_name: "shield-check", title: "Amplie", body: "Aos poucos." },
];

function intro(): LocalizedSlideReview {
  return {
    slide_index: 1,
    slide_type: "intro",
    presentation_pt: { heading: "Título", body: "Corpo.", tldr_strip: TLDR_PT },
    presentation_en: { heading: "Title", body: "Body." },
  };
}

function closing(): LocalizedSlideReview {
  return {
    slide_index: 6,
    slide_type: "closing",
    presentation_pt: { heading: "Comece", body: "Corpo.", actions: ACTIONS_PT },
    presentation_en: { heading: "Start", body: "Body." },
  };
}

describe("mirrorLocaleStructure (AE-0430)", () => {
  // Scenario: The EN column shows a TL;DR field when only PT has one
  it("adds an empty TL;DR the other locale has", () => {
    const slide = intro();
    const mirrored = mirrorLocaleStructure(
      slide.presentation_en,
      slide.presentation_pt,
    );
    expect(mirrored).toEqual({
      heading: "Title",
      body: "Body.",
      tldr_strip: "",
    });
    expect(slide.presentation_en).not.toHaveProperty("tldr_strip");
  });

  // Scenario: The EN column shows the PT items when EN has no item list
  it("adds the PT items with empty texts and the PT icons", () => {
    const slide = closing();
    const mirrored = mirrorLocaleStructure(
      slide.presentation_en,
      slide.presentation_pt,
    );
    expect(mirrored.actions).toEqual([
      { icon_name: "target", title: "", body: "" },
      { icon_name: "eye", title: "", body: "" },
      { icon_name: "shield-check", title: "", body: "" },
    ]);
  });

  it("pads a shorter list and keeps the existing items", () => {
    const en = {
      actions: [{ icon_name: "target", title: "Pick", body: "One." }],
    };
    const mirrored = mirrorLocaleStructure(en, { actions: ACTIONS_PT });
    expect(mirrored.actions).toEqual([
      { icon_name: "target", title: "Pick", body: "One." },
      { icon_name: "eye", title: "", body: "" },
      { icon_name: "shield-check", title: "", body: "" },
    ]);
  });

  it("returns the same payload when nothing is missing", () => {
    const en = { heading: "Title", tldr_strip: "Done", actions: ACTIONS_PT };
    expect(
      mirrorLocaleStructure(en, { tldr_strip: TLDR_PT, actions: ACTIONS_PT }),
    ).toBe(en);
    expect(mirrorLocaleStructure(en, undefined)).toBe(en);
    expect(mirrorLocaleStructure(en, { tldr_strip: "", features: [] })).toBe(
      en,
    );
  });

  it("copies content_kind and blanks the text of an object extra", () => {
    const mirrored = mirrorLocaleStructure(
      {},
      { content_kind: "insight", insight: { title: "T", body: "B", tone: 1 } },
    );
    expect(mirrored).toEqual({
      content_kind: "insight",
      insight: { title: "", body: "", tone: 1 },
    });
  });

  it("leaves a non-item value of the other locale out", () => {
    expect(mirrorLocaleStructure({}, { stats: 3 })).toEqual({});
    expect(mirrorLocaleStructure({}, { actions: ["raw"] }).actions).toEqual([
      "raw",
    ]);
  });

  it("maps each locale to the other", () => {
    expect(otherLocaleKey("presentation_pt")).toBe("presentation_en");
    expect(otherLocaleKey("presentation_en")).toBe("presentation_pt");
  });
});

describe("editing mirrored fields (AE-0430)", () => {
  // Scenario: Typing in the mirrored EN TL;DR creates the field on the EN payload
  it("creates the EN TL;DR on the first edit", () => {
    const [edited] = applySlideExtraEdit([intro()], {
      slideIndex: 1,
      locale: "presentation_en",
      extraKey: "tldr_strip",
      value: "Grok Bot books by phone",
    });
    expect(edited!.presentation_en.tldr_strip).toBe("Grok Bot books by phone");
  });

  // Scenario: Editing a mirrored EN item creates the EN list from the PT shape
  it("creates the EN action list with the PT icons", () => {
    const [edited] = applySlideStructuredItemEdit([closing()], {
      slideIndex: 6,
      locale: "presentation_en",
      listKey: "actions",
      itemIndex: 1,
      field: "body",
      value: "Read every step.",
    });
    expect(edited!.presentation_en.actions).toEqual([
      { icon_name: "target", title: "", body: "" },
      { icon_name: "eye", title: "", body: "Read every step." },
      { icon_name: "shield-check", title: "", body: "" },
    ]);
  });

  // Scenario: An untouched slide is not sent as changed
  it("does not mark an unedited slide as changed", () => {
    const original = [intro(), closing()];
    const edited = applySlideExtraEdit(original, {
      slideIndex: 1,
      locale: "presentation_en",
      extraKey: "tldr_strip",
      value: "Typed",
    });
    expect(
      changedLocalizedSlides(original, edited).map((s) => s.slide_index),
    ).toEqual([1]);
  });
});
