/**
 * Gherkin: frontend/tests/features/content-review-en-structure-ae0430.feature.
 */
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { LocalizedSlideReview } from "@/modules/publishing";
import { ContentLocaleFields } from "./content-phase-locale-fields";

const TLDR_PT = "Grok Bot, reserva por telefone, agente com computador próprio";
const TLDR_LABEL = "Summary strip (TL;DR)";

function slide(): LocalizedSlideReview {
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
    presentation_pt: {
      heading: "Comece",
      body: "Corpo.",
      actions: [
        { icon_name: "target", title: "Escolha", body: "Um comando." },
        { icon_name: "eye", title: "Acompanhe", body: "Leia." },
      ],
    },
    presentation_en: { heading: "Start", body: "Body." },
  };
}

function renderEditable(
  review: LocalizedSlideReview,
  onExtraChange = vi.fn(),
): ReturnType<typeof render> {
  return render(
    <ContentLocaleFields
      slide={review}
      localeKey="presentation_en"
      localeLabel="EN"
      fieldErrors={new Map()}
      onCopyChange={vi.fn()}
      onStructuredItemChange={vi.fn()}
      onExtraChange={onExtraChange}
    />,
  );
}

describe("ContentLocaleFields — EN mirrors PT structure (AE-0430)", () => {
  // Scenario: The EN column shows a TL;DR field when only PT has one
  it("shows an empty, editable EN TL;DR", () => {
    renderEditable(slide());
    const field = screen.getByLabelText(TLDR_LABEL);
    expect(field).toHaveValue("");
  });

  // Scenario: Typing in the mirrored EN TL;DR creates the field on the EN payload
  it("sends the typed EN TL;DR as an extra edit", () => {
    const onExtraChange = vi.fn();
    renderEditable(slide(), onExtraChange);
    fireEvent.change(screen.getByLabelText(TLDR_LABEL), {
      target: { value: "Grok Bot books by phone" },
    });
    expect(onExtraChange).toHaveBeenCalledWith({
      slideIndex: 1,
      locale: "presentation_en",
      extraKey: "tldr_strip",
      field: undefined,
      value: "Grok Bot books by phone",
    });
  });

  // Scenario: The EN column shows the PT items when EN has no item list
  it("shows the PT action items as empty EN items", () => {
    renderEditable(closing());
    const titles = screen.getAllByLabelText("Item title");
    expect(titles).toHaveLength(2);
    expect(titles[0]).toHaveValue("");
  });

  it("keeps a read-only EN column as it is stored", () => {
    render(
      <ContentLocaleFields
        slide={slide()}
        localeKey="presentation_en"
        localeLabel="EN"
        fieldErrors={new Map()}
      />,
    );
    expect(screen.queryByText(TLDR_LABEL)).toBeNull();
  });
});
