import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";

describe("NeonTopBar", () => {
  it("renders title and breadcrumb", () => {
    render(
      <NeonTopBar title="Dashboard" breadcrumb={[{ label: "overview" }]} />,
    );
    expect(
      screen.getByRole("heading", { name: "Dashboard" }),
    ).toBeInTheDocument();
    expect(screen.getByText("overview")).toBeInTheDocument();
  });

  it("renders action slot content", () => {
    render(
      <NeonTopBar
        title="Workflow"
        actions={<button type="button">New Card</button>}
      />,
    );
    expect(
      screen.getByRole("button", { name: "New Card" }),
    ).toBeInTheDocument();
  });
});
