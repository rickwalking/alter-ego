import { it, expect, vi, beforeEach, describe } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { createElement } from "react";
import { SlideTextEditSection } from "./slide-text-edit-section";
import type { LocalizedSlideReview } from "@/modules/publishing/blog/types-ai";
import type { EditCarouselSlidesResponse } from "@/modules/publishing/distribution/hooks/use-edit-carousel-slides";

// AE-0403 — Gherkin: frontend/tests/features/review-form-field-errors.feature
// (uses the real en messages from the global next-intl mock).

vi.mock(
  "@/modules/publishing/distribution/hooks/use-edit-carousel-slides",
  () => ({ useEditCarouselSlides: vi.fn() }),
);
vi.mock(
  "@/modules/publishing/distribution/hooks/use-republish-carousel",
  () => ({ useRepublishCarousel: vi.fn() }),
);

import { useEditCarouselSlides } from "@/modules/publishing/distribution/hooks/use-edit-carousel-slides";
import { useRepublishCarousel } from "@/modules/publishing/distribution/hooks/use-republish-carousel";

const EN_BODY_ID = "#publish-edit-9-presentation_en-body";
const EMPHASIS_MESSAGE = "Emphasis must use balanced <strong>…</strong> tags";

const republishMutate = vi.fn();
const editMutate = vi.fn();

type FieldViolation = NonNullable<
  EditCarouselSlidesResponse["field_violations"]
>[number];

function emphasisViolation(): FieldViolation {
  return {
    code: "emphasis_markup_invalid",
    message: "Emphasis must use balanced <strong>...</strong> tags only",
    severity: "blocker",
    slide_index: 9,
    locale: "en",
    field: "body",
  };
}

function response(violations: FieldViolation[]): EditCarouselSlidesResponse {
  return {
    project_id: "proj-1",
    status: "updated",
    validation: { blocking: violations.length > 0, violations },
    field_violations: violations,
  };
}

function slides(): LocalizedSlideReview[] {
  return [
    {
      slide_index: 9,
      slide_type: "summary",
      presentation_pt: {
        heading: "Título",
        body: "Corpo **forte**.",
        summary_points: [{ title: "Ponto", body: "Corpo do ponto" }],
      },
      presentation_en: { heading: "Title", body: "Body <strong>x" },
    },
  ];
}

/** Each mutate call answers with the next queued response. */
function queueResponses(...responses: EditCarouselSlidesResponse[]): void {
  const queue = [...responses];
  editMutate.mockImplementation(
    (
      _vars: unknown,
      options?: { onSuccess?: (data: EditCarouselSlidesResponse) => void },
    ) => {
      const next = queue.shift();
      if (next) {
        options?.onSuccess?.(next);
      }
    },
  );
}

function field(selector: string): HTMLTextAreaElement {
  const element = document.querySelector<HTMLTextAreaElement>(selector);
  if (!element) {
    throw new Error(`missing field ${selector}`);
  }
  return element;
}

function openAndSave(): void {
  fireEvent.click(screen.getByText("Edit text"));
  fireEvent.change(field(EN_BODY_ID), { target: { value: "Body <strong>y" } });
  fireEvent.click(screen.getByText("Save changes"));
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useEditCarouselSlides).mockReturnValue({
    mutate: editMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useEditCarouselSlides>);
  vi.mocked(useRepublishCarousel).mockReturnValue({
    mutate: republishMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useRepublishCarousel>);
  render(
    createElement(SlideTextEditSection, {
      projectId: "proj-1",
      slides: slides(),
      runInProgress: false,
      onEdited: vi.fn(),
    }),
  );
});

describe("SlideTextEditSection field errors (AE-0403)", () => {
  // Scenario: A refused save flags the offending field
  it("flags the offending field with aria-invalid and a described message", () => {
    queueResponses(response([emphasisViolation()]));
    openAndSave();

    const body = field(EN_BODY_ID);
    expect(body).toHaveAttribute("aria-invalid", "true");
    expect(body.className).toContain("border-destructive");
    const describedBy = body.getAttribute("aria-describedby");
    expect(describedBy).toBe("publish-edit-9-presentation_en-body-error");
    expect(document.getElementById(describedBy ?? "")).toHaveTextContent(
      EMPHASIS_MESSAGE,
    );
    expect(document.activeElement).toBe(body);
    expect(field("#publish-edit-9-presentation_pt-body")).not.toHaveAttribute(
      "aria-invalid",
    );
    expect(republishMutate).not.toHaveBeenCalled();
  });

  // Scenario: A per-slide summary sits at the bottom of the slide form
  it("lists the slide summary and links the slide from the global notice", () => {
    queueResponses(response([emphasisViolation()]));
    openAndSave();

    const summary = screen.getByRole("list", { name: "Slide 9 errors" });
    expect(summary).toHaveTextContent(`Slide 9 · EN body: ${EMPHASIS_MESSAGE}`);
    const notice = screen.getByRole("alert");
    expect(notice).toHaveTextContent("Fix the highlighted fields");
    field("#publish-edit-9-presentation_pt-heading").focus();
    fireEvent.click(within(notice).getByRole("button", { name: "Slide 9" }));
    expect(document.activeElement).toBe(field(EN_BODY_ID));
  });

  // Scenario: A structured-item violation is shown on the item field
  it("flags a structured item body and labels it in the summary", () => {
    queueResponses(
      response([
        {
          code: "body_too_long",
          message: "summary_points[0].body exceeds max 90 characters (got 120)",
          severity: "blocker",
          slide_index: 9,
          locale: "pt",
          field: "summary_points[0].body",
          item_list: "summary_points",
          item_index: 0,
          item_field: "body",
        },
      ]),
    );
    openAndSave();

    const item = field("#publish-edit-9-presentation_pt-summary_points-0-body");
    expect(item).toHaveAttribute("aria-invalid", "true");
    expect(
      document.getElementById(item.getAttribute("aria-describedby") ?? ""),
    ).toHaveTextContent("Body too long (max 90 characters)");
    expect(
      screen.getByRole("list", { name: "Slide 9 errors" }),
    ).toHaveTextContent("Slide 9 · PT item 1 · body: Body too long");
  });

  // Scenario: An unknown violation code falls back to the backend message
  it("falls back to the backend message for an unknown code", () => {
    queueResponses(
      response([
        { ...emphasisViolation(), code: "some_new_rule", message: "Nope" },
      ]),
    );
    openAndSave();

    expect(
      screen.getByRole("list", { name: "Slide 9 errors" }),
    ).toHaveTextContent("Slide 9 · EN body: Nope");
  });

  // Scenario: Editing a flagged field clears its error
  it("clears a field's error as soon as that field is edited", () => {
    queueResponses(response([emphasisViolation()]));
    openAndSave();

    fireEvent.change(field(EN_BODY_ID), {
      target: { value: "Body <strong>y</strong>" },
    });
    expect(field(EN_BODY_ID)).not.toHaveAttribute("aria-invalid");
    expect(
      screen.queryByRole("list", { name: "Slide 9 errors" }),
    ).not.toBeInTheDocument();
  });

  // Scenario: Submitting manual fixes succeeds
  it("re-submits manual fixes and clears every error on success", () => {
    queueResponses(response([emphasisViolation()]), response([]));
    openAndSave();

    const submit = screen.getByRole("button", { name: "Submit manual fixes" });
    expect(submit).toBeDisabled();
    expect(screen.queryByText("Save changes")).not.toBeInTheDocument();
    fireEvent.change(field(EN_BODY_ID), {
      target: { value: "Body <strong>y</strong>" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Submit manual fixes" }),
    );

    expect(editMutate).toHaveBeenCalledTimes(2);
    const [vars] = editMutate.mock.calls[1] as [
      { editedSlides: LocalizedSlideReview[] },
    ];
    expect(vars.editedSlides[0]?.presentation_en.body).toBe(
      "Body <strong>y</strong>",
    );
    expect(republishMutate).toHaveBeenCalledTimes(1);
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
    expect(document.querySelector("[aria-invalid]")).toBeNull();
  });

  // Scenario: Submitting manual fixes is refused again
  it("shows the new field errors on a second refusal", () => {
    queueResponses(
      response([emphasisViolation()]),
      response([
        {
          ...emphasisViolation(),
          code: "heading_not_sentence_case_en",
          message: "English heading must start with an uppercase letter",
          field: "heading",
        },
      ]),
    );
    openAndSave();
    fireEvent.change(field(EN_BODY_ID), {
      target: { value: "Body <strong>y</strong>" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Submit manual fixes" }),
    );

    const heading = field("#publish-edit-9-presentation_en-heading");
    expect(heading).toHaveAttribute("aria-invalid", "true");
    expect(field(EN_BODY_ID)).not.toHaveAttribute("aria-invalid");
    expect(
      screen.getByRole("list", { name: "Slide 9 errors" }),
    ).toHaveTextContent(
      "Slide 9 · EN heading: The English heading must start with a capital letter",
    );
    expect(
      screen.getByRole("button", { name: "Submit manual fixes" }),
    ).toBeDisabled();
    expect(republishMutate).not.toHaveBeenCalled();
  });
});
