/**
 * The persona card and empty state rendered with the real Portuguese messages.
 *
 * Gherkin: tests/features/personas-polish-ae0513.feature
 */
import { render as renderBare, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import pt from "@/i18n/locales/pt.json";
import type { PersonaProfile } from "@/modules/persona";
import { PersonaTile } from "./persona-tile";
import { PersonasEmptyState } from "./personas-empty-state";

vi.mock("next-intl", async (importOriginal) => importOriginal());

const PERSONA: PersonaProfile = {
  id: "p-1",
  name: "123 ⚙",
  description: null,
  tone_attributes: { formal: 0.3, conversational: 0.8, humorous: 0.4 },
  writing_samples: [],
  forbidden_phrases: [],
  preferred_phrases: [],
  sentence_structure_preferences: null,
  paragraph_style: null,
  opinion_expression: null,
  expertise_areas: ["A1", "A2", "A3", "A4", "A5", "A6", "A7"],
  created_at: "2026-10-21T00:00:00Z",
  updated_at: "2026-10-21T00:00:00Z",
  version: 1,
};

function render(ui: React.ReactElement): ReturnType<typeof renderBare> {
  return renderBare(ui, {
    wrapper: ({ children }) => (
      <NextIntlClientProvider
        locale="pt"
        messages={pt}
        timeZone="America/Sao_Paulo"
      >
        {children}
      </NextIntlClientProvider>
    ),
  });
}

describe("personas in Portuguese", () => {
  it("translates the missing description and the avatar label", () => {
    // Scenario: A persona without a description says so in the page language
    // Scenario: A name without letters shows an avatar icon
    render(
      <PersonaTile persona={PERSONA} onEdit={vi.fn()} onDelete={vi.fn()} />,
    );
    expect(screen.getByText("Sem descrição")).toBeInTheDocument();
    expect(
      screen.getByRole("img", { name: "Avatar de 123 ⚙" }),
    ).toBeInTheDocument();
    expect(
      screen.getByText("Mais áreas de especialidade: 1"),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Editar a persona 123 ⚙" }),
    ).toBeInTheDocument();
  });

  it("shows the empty state title and action in Portuguese", () => {
    // Scenario: An empty persona list shows a welcoming empty state with the primary action
    render(<PersonasEmptyState searchQuery="" onCreate={vi.fn()} />);
    expect(
      screen.getByRole("heading", { name: "Nenhuma persona ainda" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Criar a primeira persona" }),
    ).toBeInTheDocument();
  });
});
