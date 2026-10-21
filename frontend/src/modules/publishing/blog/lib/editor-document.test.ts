import { describe, expect, it } from "vitest";
import {
  EN_1,
  SEC_1,
  SEC_2,
  SEC_3,
  image,
  v2Document,
} from "../editor.test-utils";
import {
  activeDocument,
  addSection,
  applySuggestion,
  deleteSection,
  moveSection,
  newSectionId,
  normalizeForSave,
  setCover,
  slotImage,
  updateSection,
  withServerBody,
  withServerImage,
  withServerTranslation,
} from "./editor-document";

// Scenarios: tests/features/blog_editor_ae0424.feature

describe("section edits (AE-0424)", () => {
  // Scenario: Editing a section heading and body persists it
  it("updates one section and keeps the others", () => {
    const doc = updateSection(v2Document(), "pt", {
      id: SEC_1,
      patch: { heading: "Novo", body_md: "Novo corpo" },
    });
    expect(doc.sections[0]).toMatchObject({
      heading: "Novo",
      body_md: "Novo corpo",
    });
    expect(doc.sections[1]).toEqual(v2Document().sections[1]);
  });

  // Scenario: Adding a section inserts a new stable id
  it("appends a section with a fresh sec_<uuid4> id", () => {
    const doc = addSection(v2Document(), "pt");
    expect(doc.sections).toHaveLength(4);
    expect(doc.sections[3]!.id).toMatch(/^sec_[0-9a-f-]{36}$/);
    expect(newSectionId()).not.toBe(newSectionId());
  });

  // Scenario: Deleting a section removes it without touching the others
  it("deletes the middle section and keeps ids and order", () => {
    const doc = deleteSection(v2Document(), "pt", SEC_2);
    expect(doc.sections.map((s) => s.id)).toEqual([SEC_1, SEC_3]);
  });

  // Scenario: Reordering sections keeps each section's own image
  it("moves a section with its own image and id", () => {
    const doc = moveSection(v2Document(), "pt", { id: SEC_1, delta: 1 });
    expect(doc.sections.map((s) => s.id)).toEqual([SEC_2, SEC_1, SEC_3]);
    expect(doc.sections[1]!.image?.url).toBe("https://cdn.example/1.jpg");
  });

  it("ignores a move past either end or of an unknown id", () => {
    const original = v2Document();
    expect(
      moveSection(original, "pt", { id: SEC_1, delta: -1 }).sections,
    ).toEqual(original.sections);
    expect(
      moveSection(original, "pt", { id: SEC_3, delta: 1 }).sections,
    ).toEqual(original.sections);
    expect(
      moveSection(original, "pt", { id: "sec_x", delta: 1 }).sections,
    ).toEqual(original.sections);
  });
});

describe("language subtrees (AE-0424)", () => {
  // Scenario: Editing the EN document never mutates PT
  it("edits EN without touching PT", () => {
    const original = v2Document(true);
    const doc = updateSection(original, "en", {
      id: EN_1,
      patch: { body_md: "Edited" },
    });
    expect(doc.translations.en!.sections[0]!.body_md).toBe("Edited");
    expect(JSON.stringify({ ...doc, translations: {} })).toBe(
      JSON.stringify({ ...original, translations: {} }),
    );
    expect(setCover(doc, "en", image()).cover).toBeNull();
  });

  // Scenario: A missing EN translation is read-only with a generate action
  it("has no EN document (and edits are no-ops) when the translation is missing", () => {
    const doc = v2Document();
    expect(activeDocument(doc, "en")).toBeNull();
    expect(addSection(doc, "en")).toBe(doc);
    expect(slotImage(doc, { language: "en", sectionId: null })).toBeNull();
  });

  it("reads cover and section images of a slot", () => {
    const doc = setCover(
      v2Document(),
      "pt",
      image("https://cdn.example/c.jpg"),
    );
    expect(slotImage(doc, { language: "pt", sectionId: null })?.url).toBe(
      "https://cdn.example/c.jpg",
    );
    expect(slotImage(doc, { language: "pt", sectionId: SEC_2 })?.url).toBe(
      "https://cdn.example/2.jpg",
    );
    expect(slotImage(doc, { language: "pt", sectionId: "sec_x" })).toBeNull();
  });
});

describe("server merges (AE-0424)", () => {
  it("takes only the generated image slot from the server", () => {
    const server = updateSection(v2Document(), "pt", {
      id: SEC_3,
      patch: { image: image("/api/blog-images/p/n.jpg") },
    });
    const draft = updateSection(v2Document(), "pt", {
      id: SEC_1,
      patch: { body_md: "Digitando" },
    });
    const merged = withServerImage(draft, server, {
      language: "pt",
      sectionId: SEC_3,
    });
    expect(merged.sections[2]!.image?.url).toBe("/api/blog-images/p/n.jpg");
    expect(merged.sections[0]!.body_md).toBe("Digitando");
  });

  it("takes the server cover", () => {
    const server = setCover(
      v2Document(),
      "pt",
      image("/api/blog-images/p/c.jpg"),
    );
    expect(
      withServerImage(v2Document(), server, { language: "pt", sectionId: null })
        .cover?.url,
    ).toBe("/api/blog-images/p/c.jpg");
  });

  // Scenario: Rewrite this section in my voice replaces only that section
  it("takes only the rewritten body", () => {
    const server = updateSection(v2Document(), "pt", {
      id: SEC_2,
      patch: { body_md: "Na minha voz" },
    });
    const merged = withServerBody(v2Document(), server, {
      language: "pt",
      sectionId: SEC_2,
    });
    expect(merged.sections.map((s) => s.body_md)).toEqual([
      "Corpo um",
      "Na minha voz",
      "Corpo três",
    ]);
    expect(
      withServerBody(v2Document(), server, {
        language: "pt",
        sectionId: "sec_x",
      }),
    ).toEqual(v2Document());
  });

  it("takes the server EN translation and leaves PT alone", () => {
    const merged = withServerTranslation(v2Document(), v2Document(true));
    expect(merged.translations.en!.sections[0]!.id).toBe(EN_1);
    expect(withServerTranslation(v2Document(), v2Document())).toEqual(
      v2Document(),
    );
  });
});

describe("normalizeForSave / applySuggestion", () => {
  it("stores blank headings as null in every language", () => {
    const doc = updateSection(v2Document(true), "en", {
      id: EN_1,
      patch: { heading: "  " },
    });
    const normalized = normalizeForSave(
      updateSection(doc, "pt", { id: SEC_1, patch: { heading: "" } }),
    );
    expect(normalized.sections[0]!.heading).toBeNull();
    expect(normalized.translations.en!.sections[0]!.heading).toBeNull();
    expect(normalized.sections[1]!.heading).toBe("Dois");
  });

  it("replaces the selected text of the selected section", () => {
    const doc = applySuggestion(v2Document(), {
      language: "pt",
      selection: { sectionId: SEC_2, text: "dois" },
      text: "2",
    });
    expect(doc.sections[1]!.body_md).toBe("Corpo 2");
  });

  it("does nothing without a selection or when the text is gone", () => {
    const base = v2Document();
    expect(
      applySuggestion(base, { language: "pt", selection: null, text: "x" }),
    ).toBe(base);
    expect(
      applySuggestion(base, {
        language: "pt",
        selection: { sectionId: SEC_2, text: "zzz" },
        text: "x",
      }),
    ).toBe(base);
  });
});
