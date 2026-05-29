import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import {
  NeonCard,
  NeonCardContent,
  NeonCardDescription,
  NeonCardFooter,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { CARD_ACCENT_COLORS, CARD_PADDING_MAP } from "@/schemas/neon-card";
import { TEXT_MUTED } from "@/constants/neon";

// Feature: NeonCard Component
describe("NeonCard Component", () => {
  // Scenario: Default card renders with dark background
  describe("When a NeonCard with content is rendered", () => {
    it("Then the card content should be visible", () => {
      render(<NeonCard>Card content</NeonCard>);
      expect(screen.getByText("Card content")).toBeInTheDocument();
    });

    it("Then default padding class should be applied", () => {
      const { container } = render(<NeonCard>Body</NeonCard>);
      expect(container.firstChild).toHaveClass(CARD_PADDING_MAP.md);
    });
  });

  // Scenario: Card with title displays header
  describe("When a NeonCard with a title is rendered", () => {
    it("Then the title should be visible", () => {
      render(<NeonCard title="Card Title">Body</NeonCard>);
      expect(screen.getByText("Card Title")).toBeInTheDocument();
    });

    it("Then subtitle should render with muted color", () => {
      render(
        <NeonCard title="Card Title" subtitle="Subtitle text">
          Body
        </NeonCard>,
      );
      const subtitle = screen.getByText("Subtitle text");
      expect(subtitle).toHaveStyle({ color: TEXT_MUTED });
    });
  });

  // Scenario: Clickable card has cursor pointer
  describe("When a NeonCard has an onClick handler", () => {
    it("Then clicking should call the handler", async () => {
      const handleClick = vi.fn();
      const user = userEvent.setup();

      render(
        <NeonCard onClick={handleClick} hover>
          Clickable
        </NeonCard>,
      );

      await user.click(screen.getByText("Clickable"));
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("Then the card should have button role and tabIndex", () => {
      render(<NeonCard onClick={vi.fn()}>Clickable</NeonCard>);
      const card = screen.getByRole("button", { name: /clickable/i });
      expect(card).toHaveAttribute("tabindex", "0");
    });

    it("Then Enter key should trigger onClick", () => {
      const handleClick = vi.fn();
      render(<NeonCard onClick={handleClick}>Press Enter</NeonCard>);
      const card = screen.getByRole("button", { name: /press enter/i });
      fireEvent.keyDown(card, { key: "Enter" });
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it("Then Space key should trigger onClick", () => {
      const handleClick = vi.fn();
      render(<NeonCard onClick={handleClick}>Press Space</NeonCard>);
      const card = screen.getByRole("button", { name: /press space/i });
      fireEvent.keyDown(card, { key: " " });
      expect(handleClick).toHaveBeenCalledTimes(1);
    });
  });

  // Scenario: Card has correct padding based on size prop
  describe("When padding prop is sm", () => {
    it("Then the card should have small padding class", () => {
      const { container } = render(
        <NeonCard padding="sm">
          Small padding
        </NeonCard>,
      );
      expect(container.firstChild).toHaveClass(CARD_PADDING_MAP.sm);
    });
  });

  describe("When padding prop is lg", () => {
    it("Then the card should have large padding class", () => {
      const { container } = render(
        <NeonCard padding="lg">
          Large padding
        </NeonCard>,
      );
      expect(container.firstChild).toHaveClass(CARD_PADDING_MAP.lg);
    });
  });

  describe("When accent prop is set", () => {
    it.each(["cyan", "magenta", "teal", "amber", "purple"] as const)(
      "Then accent %s should set top border color",
      (accent) => {
        const { container } = render(
          <NeonCard accent={accent}>
            Accented
          </NeonCard>,
        );
        expect(container.firstChild).toHaveStyle({
          borderTopColor: CARD_ACCENT_COLORS[accent],
          borderTopWidth: "2px",
        });
      },
    );
  });

  describe("When hover prop is true without onClick", () => {
    it("Then hover cursor class should be applied", () => {
      const { container } = render(
        <NeonCard hover>
          Hover only
        </NeonCard>,
      );
      expect(container.firstChild).toHaveClass("cursor-pointer");
    });
  });

  describe("NeonCard compound subcomponents", () => {
    it("Then header, title, description, content, and footer render", () => {
      render(
        <NeonCard>
          <NeonCardHeader>
            <NeonCardTitle>Title</NeonCardTitle>
            <NeonCardDescription>Description</NeonCardDescription>
          </NeonCardHeader>
          <NeonCardContent>Content</NeonCardContent>
          <NeonCardFooter>Footer</NeonCardFooter>
        </NeonCard>,
      );
      expect(screen.getByText("Title")).toBeInTheDocument();
      expect(screen.getByText("Description")).toBeInTheDocument();
      expect(screen.getByText("Content")).toBeInTheDocument();
      expect(screen.getByText("Footer")).toBeInTheDocument();
    });
  });
});
