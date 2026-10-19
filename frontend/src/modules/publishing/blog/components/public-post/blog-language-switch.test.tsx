import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { BlogLanguageSwitch } from "./blog-language-switch";

// Feature: Public blog renders the v2 document (AE-0423)
// Scenario: PT/EN content buttons switch the rendered document

const OPTIONS = [
  { language: "pt", label: "PT", href: "?lang=pt" },
  { language: "en", label: "EN", href: "?lang=en" },
];

describe("BlogLanguageSwitch", () => {
  it("links each content language through ?lang= and marks the active one", () => {
    render(
      <BlogLanguageSwitch
        activeLanguage="en"
        label="Content language"
        options={OPTIONS}
      />,
    );

    expect(
      screen.getByRole("navigation", { name: "Content language" }),
    ).toBeInTheDocument();
    const en = screen.getByRole("link", { name: "EN" });
    const pt = screen.getByRole("link", { name: "PT" });
    expect(en).toHaveAttribute("href", "?lang=en");
    expect(pt).toHaveAttribute("href", "?lang=pt");
    expect(en).toHaveAttribute("aria-current", "true");
    expect(pt).not.toHaveAttribute("aria-current");
  });
});
