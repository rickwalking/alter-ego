import { describe, it, expect, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import {
  NeonCard,
  NeonCardContent,
  NeonCardDescription,
  NeonCardFooter,
  NeonCardHeader,
  NeonCardTitle,
} from "@/components/molecules/neon-card";
import { TEXT_MUTED } from "@/constants/neon";

const CARD_TEST_ID = "card";
const BASE_CLASSES = [
  "rounded-lg",
  "border",
  "border-[var(--color-neon-card-border)]",
  "bg-bg-card",
  "text-text-primary",
  "shadow-sm",
  "transition-all",
  "duration-200",
];
const DEFAULT_PADDING_CLASS = "p-6";
const HOVER_CLASS = "cursor-pointer";

function classSet(element: HTMLElement): Set<string> {
  return new Set(element.className.split(" ").filter(Boolean));
}

describe("NeonCard root classes", () => {
  // Scenario: Default card renders with dark background
  it("renders exactly the base and default padding classes", () => {
    render(<NeonCard data-testid={CARD_TEST_ID}>Body</NeonCard>);
    expect(classSet(screen.getByTestId(CARD_TEST_ID))).toEqual(
      new Set([...BASE_CLASSES, DEFAULT_PADDING_CLASS]),
    );
  });

  it("does not apply hover classes without an onClick handler", () => {
    render(<NeonCard data-testid={CARD_TEST_ID}>Body</NeonCard>);
    const card = screen.getByTestId(CARD_TEST_ID);
    expect(card).not.toHaveClass(HOVER_CLASS);
    expect(card).not.toHaveAttribute("role");
    expect(card).not.toHaveAttribute("tabindex");
  });

  // Scenario: Clickable card has cursor pointer
  it("applies hover classes when an onClick handler is given", () => {
    render(
      <NeonCard data-testid={CARD_TEST_ID} onClick={vi.fn()}>
        Body
      </NeonCard>,
    );
    expect(screen.getByTestId(CARD_TEST_ID)).toHaveClass(HOVER_CLASS);
  });

  it("lets an explicit hover false override the onClick default", () => {
    render(
      <NeonCard data-testid={CARD_TEST_ID} hover={false} onClick={vi.fn()}>
        Body
      </NeonCard>,
    );
    expect(screen.getByTestId(CARD_TEST_ID)).not.toHaveClass(HOVER_CLASS);
  });

  it("has no accent border when no accent is given", () => {
    render(<NeonCard data-testid={CARD_TEST_ID}>Body</NeonCard>);
    const card = screen.getByTestId(CARD_TEST_ID);
    expect(card.style.borderTopWidth).toBe("");
    expect(card.style.borderTopColor).toBe("");
  });

  it("adds a two pixel accent border for a colored accent", () => {
    render(
      <NeonCard data-testid={CARD_TEST_ID} accent="cyan">
        Body
      </NeonCard>,
    );
    expect(screen.getByTestId(CARD_TEST_ID).style.borderTopWidth).toBe("2px");
  });
});

describe("NeonCard keyboard activation", () => {
  it("ignores keys other than Enter and Space", () => {
    const handleClick = vi.fn();
    render(<NeonCard onClick={handleClick}>Body</NeonCard>);
    fireEvent.keyDown(screen.getByRole("button"), { key: "a" });
    fireEvent.keyDown(screen.getByRole("button"), { key: "Escape" });
    expect(handleClick).not.toHaveBeenCalled();
  });
});

describe("NeonCard subcomponents", () => {
  // Scenario: Card with title displays header
  it("applies the header layout classes", () => {
    render(<NeonCardHeader data-testid="header" />);
    expect(screen.getByTestId("header")).toHaveClass(
      "flex",
      "flex-col",
      "space-y-1.5",
      "pb-4",
    );
  });

  it("applies the title typography classes", () => {
    render(<NeonCardTitle>Title</NeonCardTitle>);
    expect(screen.getByRole("heading", { name: "Title" })).toHaveClass(
      "text-lg",
      "font-bold",
      "leading-none",
      "tracking-tight",
    );
  });

  it("renders the description small and muted", () => {
    render(<NeonCardDescription>Muted</NeonCardDescription>);
    const description = screen.getByText("Muted");
    expect(description).toHaveClass("text-sm");
    expect(description).toHaveStyle({ color: TEXT_MUTED });
  });

  it("lets a description style override the muted color", () => {
    render(
      <NeonCardDescription style={{ color: "rgb(1, 2, 3)" }}>
        Custom
      </NeonCardDescription>,
    );
    expect(screen.getByText("Custom")).toHaveStyle({ color: "rgb(1, 2, 3)" });
  });

  it("applies the content spacing class", () => {
    render(<NeonCardContent data-testid="content" />);
    expect(screen.getByTestId("content")).toHaveClass("pt-0");
  });

  it("applies the footer layout classes", () => {
    render(<NeonCardFooter data-testid="footer" />);
    expect(screen.getByTestId("footer")).toHaveClass(
      "flex",
      "items-center",
      "pt-4",
    );
  });
});

describe("NeonCard display names", () => {
  it.each([
    [NeonCard.displayName, "NeonCard"],
    [NeonCardHeader.displayName, "NeonCardHeader"],
    [NeonCardTitle.displayName, "NeonCardTitle"],
    [NeonCardDescription.displayName, "NeonCardDescription"],
    [NeonCardContent.displayName, "NeonCardContent"],
    [NeonCardFooter.displayName, "NeonCardFooter"],
  ])("exposes %s as %s", (actual, expected) => {
    expect(actual).toBe(expected);
  });
});
