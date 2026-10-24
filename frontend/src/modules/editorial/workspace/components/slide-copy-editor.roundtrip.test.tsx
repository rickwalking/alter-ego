/**
 * Editor side of the checklist edit round trip.
 *
 * Gherkin: frontend/tests/features/checklist-wysiwyg-editor-ae0543.feature
 *
 * The fixture is shared with the backend test
 * ``backend/tests/unit/application/test_checklist_edit_roundtrip.py``, which seeds
 * generated rows, checks they are served as ``served_slide``, saves
 * ``patch_slide`` through the PATCH route and renders the slide. Here the
 * served slide goes through the real editor and must produce that payload.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { fireEvent, render } from "@testing-library/react";
import { createElement, useState } from "react";
import { describe, expect, it, vi } from "vitest";
import { WORKFLOW_PHASE_STATUS } from "@/constants/workflow";
import {
  applySlideCopyEdit,
  applySlideStructuredItemEdit,
  changedLocalizedSlides,
  resolveLocalizedSlides,
} from "@/modules/editorial/workspace/lib/presentation-slide-resolution";
import type { LocalizedSlideReview } from "@/modules/editorial/workspace/types-ai";
import { SlideCopyEditor } from "./slide-copy-editor";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

interface RoundtripEdit {
  locale: "presentation_pt" | "presentation_en";
  item_index: number;
  value: string;
}

interface RoundtripFixture {
  served_slide: LocalizedSlideReview;
  checklist_slide_indexes: number[];
  edits: RoundtripEdit[];
  patch_slide: LocalizedSlideReview;
}

const FIXTURE = JSON.parse(
  readFileSync(
    resolve(
      process.cwd(),
      "../backend/tests/fixtures/checklist_edit_roundtrip.json",
    ),
    "utf-8",
  ),
) as RoundtripFixture;

function servedItems(
  locale: RoundtripEdit["locale"],
): Record<string, unknown>[] {
  return FIXTURE.served_slide[locale].summary_points as Record<
    string,
    unknown
  >[];
}

function servedSlides(): LocalizedSlideReview[] {
  return resolveLocalizedSlides({
    project_id: "p",
    current_phase: "final_review",
    phase_status: WORKFLOW_PHASE_STATUS.AWAITING_HUMAN,
    research_findings: [],
    outline: [],
    slide_drafts: [],
    status: "completed",
    localized_slides: [FIXTURE.served_slide],
    checklist_slide_indexes: FIXTURE.checklist_slide_indexes,
  });
}

function Harness({
  slides,
  onDraft,
}: Readonly<{
  slides: LocalizedSlideReview[];
  onDraft: (draft: LocalizedSlideReview[]) => void;
}>): React.ReactElement {
  const [draft, setDraft] = useState(slides);
  onDraft(draft);
  return createElement(SlideCopyEditor, {
    slides: draft,
    idPrefix: "publish-edit",
    onCopyChange: (edit) =>
      setDraft((current) => applySlideCopyEdit(current, edit)),
    onStructuredItemChange: (edit) =>
      setDraft((current) => applySlideStructuredItemEdit(current, edit)),
  });
}

describe("checklist edit round trip (editor side)", () => {
  /** Scenario: An edit made in the editor is saved and rendered */
  it("turns the owner's line edits into the payload the backend renders", () => {
    const slides = servedSlides();
    let latest = slides;
    const { container } = render(
      createElement(Harness, {
        slides,
        onDraft: (draft) => {
          latest = draft;
        },
      }),
    );
    const lines = container.querySelectorAll<HTMLTextAreaElement>(
      "textarea[aria-label='checklistItemLabel']",
    );
    const ptLines = servedItems("presentation_pt").length;
    for (const edit of FIXTURE.edits) {
      const offset = edit.locale === "presentation_en" ? ptLines : 0;
      const field = lines[offset + edit.item_index]!;
      expect(field.value).toBe(
        servedItems(edit.locale)[edit.item_index]?.title,
      );
      fireEvent.change(field, { target: { value: edit.value } });
    }
    expect(changedLocalizedSlides(slides, latest)).toEqual([
      FIXTURE.patch_slide,
    ]);
  });
});
