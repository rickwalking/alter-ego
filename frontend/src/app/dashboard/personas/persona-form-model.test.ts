/**
 * The persona form model: starting values, backend-mirroring validation,
 * payload building and phrase entry.
 */
import { describe, expect, it } from "vitest";
import {
  addPhrase,
  initialPersonaFormState,
  newSample,
  toPersonaPayload,
  validatePersonaForm,
} from "./persona-form-model";

describe("persona form model", () => {
  it("starts a new persona with the backend's default tone", () => {
    // Scenario: An empty persona list offers to create the first persona
    const state = initialPersonaFormState();
    expect(state.tone).toEqual({
      formal: 0.3,
      conversational: 0.8,
      humorous: 0.4,
    });
    expect(state.writing_samples).toEqual([]);
  });

  it("keys each error by its field path", () => {
    // Scenario: Invalid fields block the save
    const state = {
      ...initialPersonaFormState(),
      name: "x".repeat(256),
      tone: { formal: 1.5, conversational: 0.5, humorous: -1 },
      writing_samples: [newSample("ok"), newSample(" ")],
      expertise_areas: [" "],
    };
    expect(validatePersonaForm(state)).toEqual({
      name: "errors.name",
      "tone_attributes.formal": "errors.tone",
      "tone_attributes.humorous": "errors.tone",
      "writing_samples.1": "errors.sample",
      "expertise_areas.0": "errors.invalid",
    });
  });

  it("trims the payload and sends blank text as null", () => {
    // Scenario: A new persona is created with its voice fields
    const payload = toPersonaPayload({
      ...initialPersonaFormState(),
      name: "  Ana ",
      description: "  Voice  ",
      paragraph_style: "   ",
      writing_samples: [newSample("  Post  ")],
    });
    expect(payload).toMatchObject({
      name: "Ana",
      description: "Voice",
      paragraph_style: null,
      writing_samples: ["Post"],
    });
  });

  it("adds a trimmed phrase once and ignores a blank one", () => {
    // Scenario: A new persona is created with its voice fields
    expect(addPhrase(["a"], "  b, c ")).toEqual(["a", "b, c"]);
    expect(addPhrase(["a"], "a")).toEqual(["a"]);
    expect(addPhrase(["a"], "   ")).toEqual(["a"]);
  });
});
