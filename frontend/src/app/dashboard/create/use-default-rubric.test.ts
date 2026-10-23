import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import type { QualityRubric } from "@/modules/quality";
import { buildCarouselCreateRequest } from "./helpers";
import { INITIAL_CREATE_FORM_STATE } from "./types";
import { carouselRubrics, useDefaultRubric } from "./use-default-rubric";

/** Gherkin: tests/features/carousel-rubric-ae0504.feature. */

const RUBRIC_ID = "8b0c5c58-6c7e-4c38-9d55-2a7e4f1c0001";

function rubric(overrides: Partial<QualityRubric>): QualityRubric {
  return {
    id: RUBRIC_ID,
    name: "QA",
    applicable_content_types: ["carousel"],
    is_default: false,
    ...overrides,
  } as QualityRubric;
}

function request(rubricId: string): Record<string, unknown> {
  return buildCarouselCreateRequest({
    ...INITIAL_CREATE_FORM_STATE,
    topic: "Tema",
    audience: "Devs",
    rubricId,
  });
}

describe("wizard rubric choice (AE-0504)", () => {
  /** Scenario: The wizard preselects the default carousel rubric */
  it("offers the carousel rubrics only", () => {
    expect(
      carouselRubrics([
        rubric({ id: "a", name: "Casa", is_default: true }),
        rubric({
          id: "b",
          name: "Blog",
          applicable_content_types: ["blog_post"],
        }),
      ]),
    ).toEqual([{ id: "a", name: "Casa", isDefault: true }]);
  });

  /** Scenario: The wizard preselects the default carousel rubric */
  it("preselects the default once, and nothing without a default", () => {
    const onSelect = vi.fn();
    const { rerender } = renderHook(
      ({ list }) => useDefaultRubric(list, onSelect),
      { initialProps: { list: [] as ReturnType<typeof carouselRubrics> } },
    );
    expect(onSelect).not.toHaveBeenCalled();
    rerender({
      list: [
        { id: "a", name: "A", isDefault: false },
        { id: "d", name: "D", isDefault: true },
      ],
    });
    rerender({ list: [{ id: "x", name: "X", isDefault: true }] });
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect).toHaveBeenCalledWith("d");

    const none = vi.fn();
    renderHook(() =>
      useDefaultRubric([{ id: "a", name: "A", isDefault: false }], none),
    );
    expect(none).not.toHaveBeenCalled();
  });

  /** Scenario: The chosen rubric is sent with the carousel */
  it("sends the chosen rubric, null for the policy alone, nothing by default", () => {
    expect(request(RUBRIC_ID).rubric_id).toBe(RUBRIC_ID);
    expect(request("none").rubric_id).toBeNull();
    expect(request("")).not.toHaveProperty("rubric_id");
  });
});
