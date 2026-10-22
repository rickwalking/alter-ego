import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@/test/utils";
import { INITIAL_CREATE_FORM_STATE } from "@/app/dashboard/create/types";
import { CreateModeSection } from "./create-mode-section";

/** Gherkin: tests/features/carousel-rubric-ae0504.feature. */

const RUBRICS = [
  { id: "r-house", name: "Casa", isDefault: true },
  { id: "r-qa", name: "QA", isDefault: false },
];

describe("CreateModeSection rubric select (AE-0504)", () => {
  /** Scenario: The wizard preselects the default carousel rubric */
  it("lists the carousel rubrics, marks the default and offers the policy alone", () => {
    render(
      <CreateModeSection
        form={{ ...INITIAL_CREATE_FORM_STATE, rubricId: "r-house" }}
        onChange={vi.fn()}
        personas={[]}
        rubrics={RUBRICS}
      />,
    );
    const select = screen.getByLabelText("Quality rubric");
    expect(select).toHaveValue("r-house");
    expect(
      Array.from((select as HTMLSelectElement).options).map((o) => o.text),
    ).toEqual(["Casa (default)", "QA", "Default policy (no rubric)"]);
  });

  /** Scenario: The chosen rubric is sent with the carousel */
  it("reports the owner's choice and shows the policy alone before one", () => {
    const onChange = vi.fn();
    render(
      <CreateModeSection
        form={INITIAL_CREATE_FORM_STATE}
        onChange={onChange}
        personas={[]}
        rubrics={RUBRICS}
      />,
    );
    const select = screen.getByLabelText("Quality rubric");
    expect(select).toHaveValue("none");
    fireEvent.change(select, { target: { value: "r-qa" } });
    expect(onChange).toHaveBeenCalledWith({ rubricId: "r-qa" });
  });
});
