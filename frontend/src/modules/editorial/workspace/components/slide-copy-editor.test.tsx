import { it, expect, vi } from "vitest";
import { render, fireEvent } from "@testing-library/react";
import { createElement } from "react";
import { SlideCopyEditor } from "./slide-copy-editor";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import type {
  SlideCopyEdit,
  SlideStructuredItemEdit,
} from "@/modules/editorial/workspace/lib/presentation-slide-resolution";

// AE-0314 — Gherkin: backend/tests/features/carousel_text_edit_no_regen.feature

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

function slides(body = "Corpo curto"): LocalizedSlideReview[] {
  return [
    {
      slide_index: 1,
      slide_type: "summary",
      presentation_pt: {
        heading: "titulo minusculo",
        body,
        summary_points: [{ body: "ponto antigo" }],
      },
      presentation_en: { heading: "old title", body: "Old body" },
    },
  ];
}

it("renders per-locale heading/body fields with prefixed ids", () => {
  const { container } = render(
    createElement(SlideCopyEditor, {
      slides: slides(),
      idPrefix: "publish-edit",
      onCopyChange: vi.fn(),
    }),
  );
  expect(
    container.querySelector("#publish-edit-1-presentation_pt-heading"),
  ).not.toBeNull();
  expect(
    container.querySelector("#publish-edit-1-presentation_en-body"),
  ).not.toBeNull();
});

it("fires onCopyChange with the edited value", () => {
  const onCopyChange = vi.fn<(edit: SlideCopyEdit) => void>();
  const { container } = render(
    createElement(SlideCopyEditor, {
      slides: slides(),
      idPrefix: "publish-edit",
      onCopyChange,
    }),
  );
  const heading = container.querySelector<HTMLTextAreaElement>(
    "#publish-edit-1-presentation_pt-heading",
  );
  fireEvent.change(heading!, { target: { value: "Título Corrigido" } });
  expect(onCopyChange).toHaveBeenCalledWith({
    slideIndex: 1,
    locale: "presentation_pt",
    field: "heading",
    value: "Título Corrigido",
  });
});

it("warns with a budget hint when the body exceeds the policy budget", () => {
  const contentSlides: LocalizedSlideReview[] = [
    {
      slide_index: 1,
      slide_type: "content",
      presentation_pt: { heading: "titulo", body: "x".repeat(300) },
      presentation_en: { heading: "title", body: "Body" },
    },
  ];
  const { getByRole } = render(
    createElement(SlideCopyEditor, {
      slides: contentSlides,
      idPrefix: "publish-edit",
      showBudget: true,
      policyVersion: "hero_lower_third_v1",
      onCopyChange: vi.fn(),
    }),
  );
  // The over-budget PT body raises an alert-role budget hint before submit.
  expect(getByRole("alert")).toHaveTextContent("/220 chars");
});

it("edits structured extras (summary points) when a handler is given", () => {
  const onStructuredItemChange =
    vi.fn<(edit: SlideStructuredItemEdit) => void>();
  const { container } = render(
    createElement(SlideCopyEditor, {
      slides: slides(),
      idPrefix: "publish-edit",
      onCopyChange: vi.fn(),
      onStructuredItemChange,
    }),
  );
  const items = container.querySelectorAll<HTMLTextAreaElement>(
    'textarea[aria-label="structuredItemLabel"]',
  );
  expect(items.length).toBeGreaterThan(0);
  fireEvent.change(items[0], { target: { value: "ponto novo" } });
  expect(onStructuredItemChange).toHaveBeenCalledWith(
    expect.objectContaining({
      slideIndex: 1,
      listKey: "summary_points",
      itemIndex: 0,
      field: "body",
      value: "ponto novo",
    }),
  );
});
