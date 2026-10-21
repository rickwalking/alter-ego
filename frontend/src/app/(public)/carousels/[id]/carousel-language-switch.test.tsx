import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { CarouselLanguageSwitch } from "./carousel-language-switch";

// Feature: Public carousel viewer (AE-0444)

const OPTIONS = [
  { language: "pt", label: "PT", href: "?lang=pt" },
  { language: "en", label: "EN", href: "?lang=en" },
];

describe("CarouselLanguageSwitch (AE-0444)", () => {
  it("links each language and marks the active one", () => {
    render(
      <CarouselLanguageSwitch
        activeLanguage="en"
        label="Content language"
        options={OPTIONS}
      />,
    );

    expect(screen.getByRole("navigation")).toHaveAccessibleName(
      "Content language",
    );
    expect(screen.getByRole("link", { name: "PT" })).not.toHaveAttribute(
      "aria-current",
    );
    expect(screen.getByRole("link", { name: "EN" })).toHaveAttribute(
      "aria-current",
      "true",
    );
  });
});
