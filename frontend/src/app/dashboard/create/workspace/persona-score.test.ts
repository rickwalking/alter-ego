import { describe, expect, it } from "vitest";
import { personaScoreShortfalls } from "./persona-score";

/** Mirrors backend/src/rag_backend/domain/persona_score.py. */
describe("personaScoreShortfalls", () => {
  // Scenario: A 0-10 persona score is read on the 0-100 scale
  it("reads an overall in (0, 10] as a 0-10 answer (x10)", () => {
    expect(
      personaScoreShortfalls({
        slide_1: { overall: 84 },
        slide_2: { overall: 8.7 },
      }),
    ).toEqual([]);
    expect(personaScoreShortfalls({ slide_2: { overall: 6.9 } })).toEqual([
      { key: "slide_2", slideNumber: 2, score: 69 },
    ]);
  });

  it("treats exactly 10 as the top of the 0-10 scale and 70 as passing", () => {
    expect(
      personaScoreShortfalls({
        slide_1: { overall: 10 },
        slide_2: { overall: 70 },
      }),
    ).toEqual([]);
  });

  it("keeps a score above 10 on the 0-100 scale", () => {
    expect(personaScoreShortfalls({ slide_5: { overall: 58 } })).toEqual([
      { key: "slide_5", slideNumber: 5, score: 58 },
    ]);
  });

  // Scenario: An unscored slide is ignored by the persona gate
  it("ignores 0, missing, negative, NaN and non-numeric scores", () => {
    expect(
      personaScoreShortfalls({
        slide_1: { overall: 0 },
        slide_2: {},
        slide_3: { overall: "75" },
        slide_4: { overall: Number.NaN },
        slide_5: { overall: -3 },
        slide_6: null,
        slide_7: true,
      }),
    ).toEqual([]);
  });

  it("accepts a bare number entry", () => {
    expect(personaScoreShortfalls({ slide_3: 5 })).toEqual([
      { key: "slide_3", slideNumber: 3, score: 50 },
    ]);
  });

  // Scenario: The persona hint names the slides below the threshold
  it("lists the shortfalls in slide order with rounded scores", () => {
    expect(
      personaScoreShortfalls({
        slide_8: { overall: 5.8 },
        slide_2: { overall: 6.8999999999999995 },
        hook: { overall: 40 },
      }),
    ).toEqual([
      { key: "hook", slideNumber: null, score: 40 },
      { key: "slide_2", slideNumber: 2, score: 69 },
      { key: "slide_8", slideNumber: 8, score: 58 },
    ]);
  });

  it("honours a custom threshold and empty input", () => {
    expect(personaScoreShortfalls({ slide_1: { overall: 80 } }, 85)).toEqual([
      { key: "slide_1", slideNumber: 1, score: 80 },
    ]);
    expect(personaScoreShortfalls(undefined)).toEqual([]);
    expect(personaScoreShortfalls(null)).toEqual([]);
  });
});
