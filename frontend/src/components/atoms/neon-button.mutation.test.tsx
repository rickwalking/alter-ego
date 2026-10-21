import type { ReactElement } from "react";
import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonButton, neonButtonVariants } from "@/components/atoms/neon-button";

const LABEL = "Send";
const ICON_TEST_ID = "button-icon";
const BASE_CLASSES = [
  "inline-flex",
  "items-center",
  "justify-center",
  "gap-2",
  "rounded-md",
  "font-semibold",
  "transition-all",
  "duration-200",
  "focus-visible:outline-none",
  "focus-visible:ring-2",
  "focus-visible:ring-neon-cyan",
  "focus-visible:ring-offset-2",
  "focus-visible:ring-offset-bg-deep",
  "disabled:pointer-events-none",
  "disabled:opacity-50",
];
const MD_SIZE_CLASSES = ["px-4", "py-2", "text-sm", "h-10"];

function renderIcon(): ReactElement {
  return <span data-testid={ICON_TEST_ID}>R</span>;
}

describe("NeonButton base styling", () => {
  // Scenario: Primary variant renders with cyan gradient
  it("applies the base focus and disabled classes", () => {
    render(<NeonButton>{LABEL}</NeonButton>);
    expect(screen.getByRole("button")).toHaveClass(...BASE_CLASSES);
  });

  it("maps the default size to the md size classes", () => {
    const classes = neonButtonVariants({ size: "default" }).split(" ");
    expect(classes).toEqual(expect.arrayContaining(MD_SIZE_CLASSES));
  });

  it("renders the default size through the component", () => {
    render(<NeonButton size="default">{LABEL}</NeonButton>);
    expect(screen.getByRole("button")).toHaveClass(...MD_SIZE_CLASSES);
  });
});

describe("NeonButton type attribute", () => {
  it("defaults the type attribute to button", () => {
    render(<NeonButton>{LABEL}</NeonButton>);
    expect(screen.getByRole("button")).toHaveAttribute("type", "button");
  });
});

describe("NeonButton right icon", () => {
  // Scenario: Loading state shows spinner
  it("hides a right icon while loading", () => {
    render(
      <NeonButton loading icon={renderIcon()} iconPosition="right">
        {LABEL}
      </NeonButton>,
    );
    expect(screen.queryByTestId(ICON_TEST_ID)).not.toBeInTheDocument();
  });

  it("renders no icon wrapper when iconPosition is right without an icon", () => {
    render(<NeonButton iconPosition="right">{LABEL}</NeonButton>);
    expect(
      screen.getByRole("button").querySelector('[aria-hidden="true"]'),
    ).toBeNull();
  });

  it("renders the right icon after the label", () => {
    render(
      <NeonButton icon={renderIcon()} iconPosition="right">
        {LABEL}
      </NeonButton>,
    );
    const button = screen.getByRole("button");
    expect(button.lastElementChild).toContainElement(
      screen.getByTestId(ICON_TEST_ID),
    );
    expect(button).toHaveTextContent(`${LABEL}R`);
  });
});

describe("NeonButton display name", () => {
  it("exposes a stable display name", () => {
    expect(NeonButton.displayName).toBe("NeonButton");
  });
});
