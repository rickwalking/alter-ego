/**
 * The rubric form model: starting values, backend-mirroring validation,
 * payload building and criterion reordering.
 */
import { describe, expect, it } from "vitest";
import type { QualityRubric } from "@/modules/quality";
import {
  contentTypeOptions,
  initialRubricFormState,
  moveItem,
  newCriterion,
  toRubricPayload,
  validateRubricForm,
  type RubricFormState,
} from "./rubric-form-model";

const RUBRIC: QualityRubric = {
  id: "r-1",
  name: "Legacy",
  description: null,
  criteria: [
    {
      id: "c-1",
      name: "Tone",
      description: "",
      weight: 0.3,
      evaluation_method: "unknown_method",
      min_threshold: 0.6,
      scoring_scale: "stars",
      prompt_template: "",
    },
  ],
  applicable_content_types: ["newsletter"],
  is_default: false,
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
  version: 1,
};

function validState(): RubricFormState {
  return {
    name: "Checks",
    description: "  About  ",
    applicable_content_types: ["carousel"],
    criteria: [{ ...newCriterion(), name: "Clarity" }],
  };
}

describe("rubric form model", () => {
  it("starts a new rubric as a carousel rubric without criteria", () => {
    // Scenario: An empty rubric list offers to create the first rubric
    expect(initialRubricFormState()).toEqual({
      name: "",
      description: "",
      applicable_content_types: ["carousel"],
      criteria: [],
    });
  });

  it("loads a stored rubric, mapping unknown method and scale to the first option", () => {
    // Scenario: An existing rubric is edited and saved
    const state = initialRubricFormState(RUBRIC);
    expect(state.description).toBe("");
    expect(state.applicable_content_types).toEqual(["newsletter"]);
    expect(state.criteria[0]).toMatchObject({
      weight: "0.3",
      min_threshold: "0.6",
      evaluation_method: "ai_auto",
      scoring_scale: "0-100",
    });
  });

  it("accepts a valid form and builds a trimmed payload", () => {
    // Scenario: A new rubric is created with its criteria
    const state = { ...validState(), name: "  Checks  " };
    expect(validateRubricForm(state)).toEqual({});
    const payload = toRubricPayload(state);
    expect(payload.name).toBe("Checks");
    expect(payload.description).toBe("About");
    expect(payload.criteria?.[0]).toMatchObject({
      weight: 0.5,
      min_threshold: 0.7,
    });
  });

  it("sends a blank description as null", () => {
    // Scenario: A new rubric is created with its criteria
    expect(
      toRubricPayload({ ...validState(), description: "   " }).description,
    ).toBeNull();
  });

  it("keys each error by its field path", () => {
    // Scenario: Invalid fields block the save
    const base = validState();
    const state: RubricFormState = {
      ...base,
      name: "x".repeat(256),
      applicable_content_types: [],
      criteria: [
        { ...base.criteria[0]!, name: " ", weight: "", min_threshold: "-0.1" },
      ],
    };
    expect(validateRubricForm(state)).toEqual({
      name: "errors.name",
      applicable_content_types: "errors.contentTypes",
      "criteria.0.name": "errors.criterionName",
      "criteria.0.weight": "errors.unitInterval",
      "criteria.0.min_threshold": "errors.unitInterval",
    });
  });

  it("uses the generic message for a field without its own", () => {
    // Scenario: Invalid fields block the save
    const state = { ...validState(), applicable_content_types: [""] };
    expect(validateRubricForm(state)).toEqual({
      "applicable_content_types.0": "errors.contentTypes",
    });
    const badId = { ...validState() };
    badId.criteria = [{ ...badId.criteria[0]!, id: "" }];
    expect(validateRubricForm(badId)).toEqual({
      "criteria.0.id": "errors.invalid",
    });
  });

  it("moves an item and ignores a move past either end", () => {
    // Scenario: Criteria are added, reordered and removed
    expect(moveItem(["a", "b", "c"], 2, -1)).toEqual(["a", "c", "b"]);
    expect(moveItem(["a", "b", "c"], 0, 1)).toEqual(["b", "a", "c"]);
    expect(moveItem(["a", "b"], 0, -1)).toEqual(["a", "b"]);
    expect(moveItem(["a", "b"], 1, 1)).toEqual(["a", "b"]);
  });

  it("offers the known content types plus any stored extra", () => {
    // Scenario: An existing rubric is edited and saved
    expect(contentTypeOptions(["carousel"])).toEqual(["carousel", "blog_post"]);
    expect(contentTypeOptions(["newsletter"])).toEqual([
      "carousel",
      "blog_post",
      "newsletter",
    ]);
  });

  it("gives every new criterion its own id", () => {
    // Scenario: Criteria are added, reordered and removed
    expect(newCriterion().id).not.toBe(newCriterion().id);
  });
});
