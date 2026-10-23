/**
 * Gherkin: tests/features/chat-a11y-i18n.feature
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import PublicChatLayout from "./layout";

describe("PublicChatLayout", () => {
  /** Scenario: The public chat has a main landmark and a skip link */
  it("starts with a skip link to the main content", () => {
    render(
      <PublicChatLayout>
        <main id="main-content">chat</main>
      </PublicChatLayout>,
    );
    expect(
      screen.getByRole("link", { name: "Skip to content" }),
    ).toHaveAttribute("href", "#main-content");
  });
});
