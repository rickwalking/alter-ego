import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { BlogEmptyState } from "./blog-empty-state";

const OWNER_INSTRUCTION = /generate|gere|create one|crie/i;

describe("public blog empty state", () => {
  // Scenario: The empty blog speaks to visitors and links the carousels
  it("tells visitors no articles are published and links the carousels", () => {
    render(
      <BlogEmptyState
        message={en.blog.noPosts}
        linkLabel={en.blog.browseCarousels}
      />,
    );
    expect(screen.getByText(en.blog.noPosts)).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: en.blog.browseCarousels }),
    ).toHaveAttribute("href", "/carousels");
    expect(screen.queryByText(OWNER_INSTRUCTION)).not.toBeInTheDocument();
  });

  // Scenario: The empty-state copy exists in both languages without owner instructions
  it.each([
    ["en", en.blog],
    ["pt", pt.blog],
  ])("has %s visitor copy without owner instructions", (_, blog) => {
    expect(blog.noPosts).not.toMatch(OWNER_INSTRUCTION);
    expect(blog.browseCarousels.length).toBeGreaterThan(0);
  });
});
