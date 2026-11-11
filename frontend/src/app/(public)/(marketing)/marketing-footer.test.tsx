import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { MarketingFooter } from "@/app/(public)/(marketing)/marketing-footer";

// Scenario: The marketing footer links the privacy policy
describe("MarketingFooter", () => {
  it("links the privacy policy next to the copyright", () => {
    render(<MarketingFooter privacyLabel="Privacidade" />);

    expect(screen.getByText("© 2026 Pedro Marins")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Privacidade" })).toHaveAttribute(
      "href",
      "/privacidade",
    );
  });
});
