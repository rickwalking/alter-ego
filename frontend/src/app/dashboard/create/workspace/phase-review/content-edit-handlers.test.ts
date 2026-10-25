import { describe, expect, it, vi } from "vitest";
import { contentEditHandlers } from "./content-edit-handlers";
import type { LocalizedSlideReview } from "@/modules/publishing";

const SLIDES = [
  {
    slide_index: 2,
    slide_type: "summary",
    presentation_pt: { heading: "Resumo", body: "", summary_points: [] },
    presentation_en: { heading: "Summary", body: "", summary_points: [] },
  },
] as unknown as LocalizedSlideReview[];

describe("contentEditHandlers", () => {
  // Scenario: Adding an item clears the list error
  it("adding an item clears the list-level error of both locales", () => {
    const clearField = vi.fn<(key: string) => void>();
    const onSlidesChange = vi.fn();
    const handlers = contentEditHandlers(SLIDES, onSlidesChange, clearField);

    handlers.onStructuredListChange({
      slideIndex: 2,
      listKey: "summary_points",
      operation: "add",
    });

    expect(onSlidesChange).toHaveBeenCalledOnce();
    expect(clearField.mock.calls.map(([key]) => key)).toEqual([
      "2:presentation_pt:summary_points",
      "2:presentation_en:summary_points",
    ]);
  });
});
