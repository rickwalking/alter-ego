import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { VoiceMatchScorer } from "./voice-match-scorer";

const translate = (key: string): string => `blogEditorial.${key}`;
vi.mock("next-intl", () => ({
  useTranslations: () => translate,
}));

const authenticatedFetch = vi.fn<(...args: unknown[]) => Promise<Response>>();
vi.mock("@/lib/authenticated-fetch", () => ({
  authenticatedFetch: (...args: unknown[]) => authenticatedFetch(...args),
}));

describe("VoiceMatchScorer", () => {
  it("shows the translated error when scoring fails", async () => {
    // Scenario: A failed voice score shows a translated error
    authenticatedFetch.mockResolvedValueOnce(new Response("", { status: 500 }));
    render(<VoiceMatchScorer personaId="persona-1" />);

    fireEvent.change(screen.getByRole("textbox"), {
      target: { value: "Some text" },
    });
    fireEvent.click(screen.getByRole("button"));

    expect(
      await screen.findByText("blogEditorial.voiceScoreFailed"),
    ).toBeInTheDocument();
  });
});
