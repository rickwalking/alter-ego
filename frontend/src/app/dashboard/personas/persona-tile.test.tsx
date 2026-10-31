/**
 * The persona card on the personas page: avatar, translated fallbacks,
 * hidden-expertise chip and the touch-sized actions inside the card.
 *
 * Gherkin: tests/features/personas-polish-ae0513.feature
 */
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import type { PersonaProfile } from "@/modules/persona";
import { PersonaTile } from "./persona-tile";

const BASE: PersonaProfile = {
  id: "p-1",
  name: "Pedro",
  description: "Tech lead voice",
  tone_attributes: { formal: 0.2, conversational: 0.9, humorous: 0.5 },
  writing_samples: [],
  forbidden_phrases: [],
  preferred_phrases: [],
  sentence_structure_preferences: null,
  paragraph_style: null,
  opinion_expression: null,
  expertise_areas: ["AI"],
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
  version: 1,
};

function renderTile(overrides: Partial<PersonaProfile> = {}): {
  onEdit: () => void;
  onDelete: () => void;
} {
  const onEdit = vi.fn();
  const onDelete = vi.fn();
  render(
    <PersonaTile
      persona={{ ...BASE, ...overrides }}
      onEdit={onEdit}
      onDelete={onDelete}
    />,
  );
  return { onEdit, onDelete };
}

describe("PersonaTile", () => {
  it("shows the first letter of a name that starts with a bracket", () => {
    // Scenario: The avatar shows the first letter of the name
    renderTile({ name: "[Ágata] rascunho" });
    expect(screen.getByTestId("persona-avatar")).toHaveTextContent(/^Á$/);
  });

  it("uppercases a lowercase initial", () => {
    // Scenario: The avatar initial is uppercased
    renderTile({ name: "élan" });
    expect(screen.getByTestId("persona-avatar")).toHaveTextContent(/^É$/);
  });

  it("shows a labelled icon when the name has no letter", () => {
    // Scenario: A name without letters shows an avatar icon
    renderTile({ name: "123 ⚙" });
    const avatar = screen.getByTestId("persona-avatar");
    expect(
      within(avatar).getByRole("img", { name: "Avatar of 123 ⚙" }),
    ).toBeInTheDocument();
    expect(avatar.textContent).toBe("");
  });

  it("says when a persona has no description", () => {
    // Scenario: A persona without a description says so in the page language
    renderTile({ description: null, opinion_expression: "  " });
    expect(screen.getByText("No description")).toBeInTheDocument();
    expect(screen.queryByText(/provided/)).not.toBeInTheDocument();
  });

  it("falls back to the opinion style before the placeholder", () => {
    // Scenario: A persona without a description says so in the page language
    renderTile({ description: "", opinion_expression: "Direct" });
    expect(screen.getByText("Direct")).toBeInTheDocument();
    expect(screen.queryByText("No description")).not.toBeInTheDocument();
  });

  it("shows the translated default role without expertise", () => {
    // Scenario: A persona without expertise gets a translated role
    renderTile({ expertise_areas: [] });
    expect(screen.getByText("Persona")).toBeInTheDocument();
    expect(screen.queryByText(/More expertise areas/)).not.toBeInTheDocument();
  });

  it("counts the expertise areas beyond the visible chips", () => {
    // Scenario: Expertise beyond the visible chips is counted
    const areas = ["A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8"];
    renderTile({ expertise_areas: areas });
    const chips = screen.getByRole("list", { name: "Expertise areas" });
    expect(within(chips).getAllByRole("listitem")).toHaveLength(7);
    expect(within(chips).getByText("+2")).toBeInTheDocument();
    expect(
      within(chips).getByText("More expertise areas (2): A7, A8"),
    ).toBeInTheDocument();
    expect(within(chips).getByText("+2").closest("li")).toHaveAttribute(
      "title",
      "A7, A8",
    );
    expect(within(chips).queryByText("A7")).not.toBeInTheDocument();
  });

  it("shows no count chip when every area fits", () => {
    // Scenario: Expertise beyond the visible chips is counted
    renderTile({ expertise_areas: ["A1", "A2", "A3", "A4", "A5", "A6"] });
    const chips = screen.getByRole("list", { name: "Expertise areas" });
    expect(within(chips).getAllByRole("listitem")).toHaveLength(6);
  });

  it("keeps touch-sized Edit and Delete inside the card", async () => {
    // Scenario: Edit and Delete sit inside the persona card as touch-sized buttons
    const user = userEvent.setup();
    const { onEdit, onDelete } = renderTile();
    const card = screen.getByTestId("persona-avatar").closest("div.flex-col");
    const edit = screen.getByRole("button", { name: "Edit persona Pedro" });
    const remove = screen.getByRole("button", { name: "Delete persona Pedro" });
    expect(card).toContainElement(edit);
    expect(card).toContainElement(remove);
    expect(edit).toHaveClass("min-h-11", "min-w-11");
    expect(remove).toHaveClass("min-h-11", "min-w-11");
    await user.click(edit);
    await user.click(remove);
    expect(onEdit).toHaveBeenCalledOnce();
    expect(onDelete).toHaveBeenCalledOnce();
  });
});
