/**
 * Gherkin: tests/features/chat-errors-ui.feature
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { ChatComposer } from "./chat-composer";

function renderComposer(value: string) {
  render(<ChatComposer value={value} onChange={vi.fn()} onSend={vi.fn()} />);
  return screen.getByRole("textbox");
}

describe("ChatComposer length limit", () => {
  /** Scenario: The composer stops at 2000 characters and shows a counter near the limit */
  it("caps the text at 2000 characters", () => {
    expect(renderComposer("hi")).toHaveAttribute("maxLength", "2000");
  });

  /** Scenario: The composer stops at 2000 characters and shows a counter near the limit */
  it("hides the counter for short messages", () => {
    const textarea = renderComposer("x".repeat(1599));
    expect(screen.queryByText(/of 2000 characters/)).not.toBeInTheDocument();
    expect(textarea).not.toHaveAttribute("aria-describedby");
  });

  /** Scenario: The composer stops at 2000 characters and shows a counter near the limit */
  it("shows the counter from 1600 characters and links it to the textarea", () => {
    const textarea = renderComposer("x".repeat(1600));
    const counter = screen.getByText("1600 of 2000 characters");
    expect(textarea).toHaveAttribute("aria-describedby", counter.id);
  });
});
