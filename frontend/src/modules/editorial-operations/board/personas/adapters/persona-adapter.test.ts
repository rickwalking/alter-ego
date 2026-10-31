/**
 * Gherkin: tests/features/personas-polish-ae0513.feature
 */
import { describe, it, expect } from "vitest";
import {
  mapPersonaProfileToCardProps,
  mapPersonaToCardProps,
} from "@/modules/editorial-operations/board/personas/adapters/persona-adapter";
import type { PersonaProfile } from "@/modules/persona";

const FALLBACKS = { description: "Sem descrição", role: "Persona" };

function profile(overrides: Partial<PersonaProfile>): PersonaProfile {
  return {
    id: "p-1",
    name: "Ana",
    description: null,
    tone_attributes: { formal: 0.3, conversational: 0.8, humorous: 0.4 },
    writing_samples: [],
    forbidden_phrases: [],
    preferred_phrases: [],
    sentence_structure_preferences: null,
    paragraph_style: null,
    opinion_expression: null,
    expertise_areas: [],
    created_at: "2026-10-21T00:00:00Z",
    updated_at: "2026-10-21T00:00:00Z",
    version: 1,
    ...overrides,
  };
}

describe("mapPersonaToCardProps", () => {
  it("maps persona fields to NeonPersonaCard props", () => {
    const result = mapPersonaToCardProps({
      name: "Pedro",
      role: "Engineer",
      description: "Builds RAG systems",
      skills: ["Python", "React"],
      avatarUrl: "/avatar.png",
    });

    expect(result).toEqual({
      name: "Pedro",
      role: "Engineer",
      description: "Builds RAG systems",
      skills: ["Python", "React"],
      avatarUrl: "/avatar.png",
    });
  });
});

describe("mapPersonaProfileToCardProps", () => {
  it("uses the given fallbacks for an empty description and role", () => {
    // Scenario: A persona without a description says so in the page language
    // Scenario: A persona without expertise gets a translated role
    expect(mapPersonaProfileToCardProps(profile({}), FALLBACKS)).toEqual({
      name: "Ana",
      role: "Persona",
      description: "Sem descrição",
      skills: [],
      hiddenSkills: [],
    });
  });

  it("keeps six areas as chips and counts the rest", () => {
    // Scenario: Expertise beyond the visible chips is counted
    const areas = ["A1", "A2", "A3", "A4", "A5", "A6", "A7"];
    const card = mapPersonaProfileToCardProps(
      profile({ description: " Voz ", expertise_areas: areas }),
      FALLBACKS,
    );
    expect(card.role).toBe("A1");
    expect(card.description).toBe("Voz");
    expect(card.skills).toEqual(areas.slice(0, 6));
    expect(card.hiddenSkills).toEqual(["A7"]);
  });
});
