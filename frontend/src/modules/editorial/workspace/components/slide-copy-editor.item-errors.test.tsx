/**
 * Checklist rule violations show under the item that needs the fix, and a
 * list-level one (too few items) under the items heading.
 *
 * Feature: frontend/tests/features/checklist-item-errors-ae0549.feature
 */
import { it, expect, vi } from "vitest";
import { render } from "@testing-library/react";
import { createElement } from "react";
import { SlideCopyEditor } from "./slide-copy-editor";
import {
  buildSlideFieldErrors,
  fieldDomId,
  fieldErrorKey,
} from "@/modules/editorial/workspace/lib/slide-field-errors";
import type {
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/editorial/workspace/types-ai";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

const PREFIX = "content-edit";

function summary(points: Record<string, string>[]): LocalizedSlideReview[] {
  return [
    {
      slide_index: 2,
      slide_type: "summary",
      presentation_pt: {
        heading: "Resumo",
        body: "Corpo",
        summary_points: points,
      },
      presentation_en: { heading: "Summary", body: "Body" },
    },
  ];
}

function violation(field: string): SlideValidationViolation {
  return {
    code: "summary_points_missing",
    message: "Summary slide needs at least 3 points with a title and a body",
    slide_index: 2,
    locale: "pt",
    field,
    severity: "blocker",
  };
}

function renderWith(
  points: Record<string, string>[],
  violations: SlideValidationViolation[],
): HTMLElement {
  const { container } = render(
    createElement(SlideCopyEditor, {
      slides: summary(points),
      idPrefix: PREFIX,
      onCopyChange: vi.fn(),
      onStructuredItemChange: vi.fn(),
      fieldErrors: buildSlideFieldErrors(violations),
    }),
  );
  return container;
}

const POINTS = [
  { title: "Um", body: "Corpo um." },
  { title: "Dois", body: "" },
  { title: "Tres", body: "Corpo tres." },
];

// Scenario: An incomplete summary point is flagged on that item
it("shows summary_points_missing under the incomplete item, not the body", () => {
  const container = renderWith(POINTS, [violation("summary_points[1].body")]);
  const itemId = fieldDomId(
    PREFIX,
    fieldErrorKey(2, "presentation_pt", "summary_points[1].body"),
  );
  const item = container.querySelector(`#${itemId}`);
  expect(item?.getAttribute("aria-invalid")).toBe("true");
  expect(container.querySelector(`#${itemId}-error`)?.textContent).toContain(
    "codes.summary_points_missing",
  );
  const bodyId = fieldDomId(
    PREFIX,
    fieldErrorKey(2, "presentation_pt", "body"),
  );
  expect(
    container.querySelector(`#${bodyId}`)?.getAttribute("aria-invalid"),
  ).toBeNull();
});

// Scenario: A too-short summary list is flagged under the items heading
it("shows a list-level summary_points_missing under the items heading", () => {
  const container = renderWith(POINTS.slice(0, 1), [
    violation("summary_points"),
  ]);
  const listId = `${fieldDomId(PREFIX, fieldErrorKey(2, "presentation_pt", "summary_points"))}-list-error`;
  expect(container.querySelector(`#${listId}`)?.textContent).toContain(
    "codes.summary_points_missing",
  );
  const empty = renderWith([], [violation("summary_points")]);
  expect(empty.querySelector(`#${listId}`)).not.toBeNull();
});
