import { fireEvent, render, screen } from "@testing-library/react";
import { useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { EDITORIAL_PHASES } from "@/constants/editorial-workflow";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import type {
  EditorialWorkflowState,
  LocalizedSlideReview,
  SlideValidationViolation,
} from "@/modules/editorial";
import {
  ContentPhaseReview,
  type ContentManualFixesActions,
} from "./content-phase-review";

/** A 300-character PT body, over the 220-character budget. */
const LONG_PT_BODY = `${"palavra ".repeat(37)}fim.`;

function contentSlide(index: number): LocalizedSlideReview {
  return {
    slide_index: index,
    slide_type: "content",
    presentation_pt: { heading: `Título ${index}`, body: `Corpo ${index}` },
    presentation_en: { heading: `Title ${index}`, body: `Body ${index}` },
  };
}

const summarySlide: LocalizedSlideReview = {
  slide_index: 2,
  slide_type: "summary",
  presentation_pt: {
    heading: "Resumo",
    summary_points: [{ icon_name: "check", title: "Ponto", body: "Corpo PT" }],
  },
  presentation_en: {
    heading: "Summary",
    summary_points: [{ icon_name: "check", title: "Point", body: "EN body" }],
  },
};

const ctaSlide: LocalizedSlideReview = {
  slide_index: 7,
  slide_type: "cta",
  presentation_pt: {
    heading: "Siga",
    creator_name: "Pedro Marins",
    creator_website: "",
  },
  presentation_en: {
    heading: "Follow",
    creator_name: "Pedro Marins",
    creator_website: "",
  },
};

const itemTooLong: SlideValidationViolation = {
  code: "body_too_long",
  message: "Body exceeds max 90 characters",
  slide_index: 2,
  locale: "en",
  field: "summary_points[0].body",
};

const slide3Blocker: SlideValidationViolation = {
  code: "slide_parse_failed",
  message: "Slide copy could not be parsed",
  slide_index: 3,
};

function stateWith(
  slides: LocalizedSlideReview[],
  violations: SlideValidationViolation[],
  drafts: Record<string, unknown>[] = [],
): EditorialWorkflowState {
  return {
    project_id: "project-1",
    current_phase: EDITORIAL_PHASES.CONTENT,
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: drafts,
    status: "draft",
    lock_version: 1,
    presentation_policy_version: "hero_lower_third_v4",
    localized_slides: slides,
    presentation_validation: {
      validation_status: violations.length ? "invalid" : "valid",
      validated_at: "2026-10-16T00:00:01Z",
      blocking: violations.length > 0,
      violations,
    },
  };
}

function field(id: string): HTMLTextAreaElement {
  const element = document.getElementById(id);
  if (!(element instanceof HTMLTextAreaElement)) {
    throw new Error(`missing field ${id}`);
  }
  return element;
}

function Harness({
  state,
  manualFixes,
}: Readonly<{
  state: EditorialWorkflowState;
  manualFixes?: ContentManualFixesActions;
}>): React.ReactElement {
  const [slides, setSlides] = useState<LocalizedSlideReview[] | undefined>();
  return (
    <ContentPhaseReview
      state={state}
      editable
      slides={slides}
      onSlidesChange={setSlides}
      manualFixes={manualFixes}
    />
  );
}

describe("ContentPhaseReview — every slide (AE-0414 B10)", () => {
  // Scenario: Every slide renders even when some drafts lack presentations
  it("renders all localized slides when only some drafts have presentations", () => {
    const slides = [1, 2, 3, 4, 5, 6, 7].map(contentSlide);
    const drafts = slides.map((slide) =>
      [1, 2, 6, 7].includes(slide.slide_index)
        ? { ...slide, title: "draft" }
        : { slide_index: slide.slide_index, title: "draft" },
    );
    render(<ContentPhaseReview state={stateWith(slides, [], drafts)} />);

    for (const index of [1, 2, 3, 4, 5, 6, 7]) {
      expect(document.getElementById(`slide-slide-${index}`)).not.toBeNull();
    }
  });

  // Scenario: A "Slide N" link focuses a real slide card
  it("focuses the slide card from its blocking-slide link", () => {
    const slides = [1, 2, 3].map(contentSlide);
    render(
      <Harness
        state={stateWith(slides, [slide3Blocker])}
        manualFixes={{ onSubmit: vi.fn() }}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: "Slide 3" }));

    expect(document.activeElement).toBe(
      document.getElementById("slide-slide-3"),
    );
  });
});

describe("ContentPhaseReview — structured fields (AE-0414 B11)", () => {
  // Scenario: A flagged summary point is editable in both locales
  it("edits a flagged summary point and submits it", () => {
    const onSubmit = vi.fn();
    render(
      <Harness
        state={stateWith([contentSlide(1), summarySlide], [itemTooLong])}
        manualFixes={{ onSubmit }}
      />,
    );
    const enBodyId = "slide-2-presentation_en-summary_points-0-body";
    expect(field("slide-2-presentation_pt-summary_points-0-title").value).toBe(
      "Ponto",
    );
    expect(field("slide-2-presentation_en-summary_points-0-title").value).toBe(
      "Point",
    );
    const enBody = field(enBodyId);
    expect(enBody).toHaveAttribute("aria-invalid", "true");
    expect(
      document.getElementById(enBody.getAttribute("aria-describedby") ?? ""),
    ).toHaveTextContent("Body too long (max 90 characters)");

    fireEvent.change(enBody, { target: { value: "Short EN body" } });
    expect(field(enBodyId)).not.toHaveAttribute("aria-invalid");
    fireEvent.click(
      screen.getByRole("button", { name: "Submit manual fixes" }),
    );

    const [sent] = onSubmit.mock.calls[0] as [LocalizedSlideReview[]];
    expect(sent).toHaveLength(1);
    expect(sent[0]!.slide_index).toBe(2);
    expect(sent[0]!.presentation_en.summary_points).toEqual([
      { icon_name: "check", title: "Point", body: "Short EN body" },
    ]);
    expect(sent[0]!.presentation_pt).toEqual(summarySlide.presentation_pt);
  });

  // Scenario: CTA structured fields show their values and are editable
  it("shows CTA values in editable fields", () => {
    render(<Harness state={stateWith([ctaSlide], [slide3Blocker])} />);

    const name = field("slide-7-presentation_pt-creator_name");
    expect(name.value).toBe("Pedro Marins");
    expect(screen.getAllByText("Creator name").length).toBeGreaterThan(0);
    expect(screen.queryByText(/Structured field: creator_name/)).toBeNull();
  });

  it("says a read-only CTA value is empty instead of showing a bare label", () => {
    render(<ContentPhaseReview state={stateWith([ctaSlide], [])} />);

    expect(screen.getAllByText("Pedro Marins")).toHaveLength(2);
    expect(screen.getAllByText("(empty)")).toHaveLength(2);
  });
});

describe("ContentPhaseReview — manual-fix payload (AE-0414 B04)", () => {
  // Scenario: Manual fixes send only the changed slides, verbatim
  it("sends only the changed slide with its untouched copy uncut", () => {
    const first: LocalizedSlideReview = {
      ...contentSlide(1),
      presentation_pt: { heading: "Título 1", body: LONG_PT_BODY },
    };
    const onSubmit = vi.fn();
    render(
      <Harness
        state={stateWith([first, contentSlide(2)], [slide3Blocker])}
        manualFixes={{ onSubmit }}
      />,
    );

    fireEvent.change(field("slide-1-presentation_en-heading"), {
      target: { value: "Title One" },
    });
    fireEvent.click(
      screen.getByRole("button", { name: "Submit manual fixes" }),
    );

    const [sent] = onSubmit.mock.calls[0] as [LocalizedSlideReview[]];
    expect(sent.map((slide) => slide.slide_index)).toEqual([1]);
    expect(sent[0]!.presentation_pt.body).toBe(LONG_PT_BODY);
    expect(sent[0]!.presentation_en.heading).toBe("Title One");
  });
});

describe("ContentPhaseReview — editing affordances (AE-0414 B29)", () => {
  // Scenario: A live counter warns when copy is over budget on a v4 deck
  it("shows a live counter that turns into an alert over budget", () => {
    render(<Harness state={stateWith([contentSlide(1)], [])} />);
    const body = field("slide-1-presentation_en-body");

    fireEvent.change(body, { target: { value: "x".repeat(5000) } });

    const alert = screen.getByRole("alert");
    expect(alert).toHaveTextContent("5000/220 characters");
    expect(alert).toHaveTextContent("over the limit");
  });

  // Scenario: Each locale states its emphasis convention
  it("hints each locale's emphasis convention", () => {
    render(<Harness state={stateWith([contentSlide(1)], [])} />);

    expect(
      screen.getByText("Emphasis in this column: use **…**"),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Emphasis in this column: use <strong>…</strong>"),
    ).toBeInTheDocument();
  });

  // Scenario: Copy using the other locale's emphasis can be converted
  it("converts PT <strong> emphasis to **", () => {
    const slide: LocalizedSlideReview = {
      ...contentSlide(6),
      presentation_pt: {
        heading: "Seis",
        body: "Com <strong>limites claros</strong>.",
      },
    };
    render(<Harness state={stateWith([slide], [])} />);

    fireEvent.click(screen.getByRole("button", { name: "Convert emphasis" }));

    expect(field("slide-6-presentation_pt-body").value).toBe(
      "Com **limites claros**.",
    );
    expect(
      screen.queryByRole("button", { name: "Convert emphasis" }),
    ).toBeNull();
  });
});

describe("ContentPhaseReview — translated violations (AE-0414 B24)", () => {
  // Scenario: Violation messages are translated
  it("shows the translated message and field label", () => {
    render(
      <ContentPhaseReview
        state={stateWith([contentSlide(1), summarySlide], [itemTooLong])}
      />,
    );

    const line = screen.getByText("body_too_long").closest("li");
    expect(line).toHaveTextContent("Slide 2");
    expect(line).toHaveTextContent("EN item 1 · body");
    expect(line).toHaveTextContent("Body too long (max 90 characters)");
    expect(line).not.toHaveTextContent("Body exceeds max 90 characters");
  });
});
