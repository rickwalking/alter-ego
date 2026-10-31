/**
 * Gherkin: tests/features/personas-polish-ae0513.feature
 */
import { describe, expect, it } from "vitest";
import { personaInitial } from "./persona-initial";

describe("personaInitial", () => {
  it("skips leading punctuation and keeps an accented letter", () => {
    // Scenario: The avatar shows the first letter of the name
    expect(personaInitial("[Ágata] rascunho")).toBe("Á");
    expect(personaInitial("¿Ágata?")).toBe("Á");
  });

  it("uppercases the first letter", () => {
    // Scenario: The avatar initial is uppercased
    expect(personaInitial("élan")).toBe("É");
    expect(personaInitial("pedro")).toBe("P");
  });

  it("skips digits, symbols and emoji", () => {
    // Scenario: The avatar shows the first letter of the name
    expect(personaInitial("42 🚀 ana")).toBe("A");
  });

  it("returns null when the name has no letter", () => {
    // Scenario: A name without letters shows an avatar icon
    expect(personaInitial("123 ⚙")).toBeNull();
    expect(personaInitial("")).toBeNull();
    expect(personaInitial("🙂 !")).toBeNull();
  });
});
