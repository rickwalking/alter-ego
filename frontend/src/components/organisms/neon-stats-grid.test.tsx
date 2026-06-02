import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonStatsGrid } from "@/components/organisms/neon-stats-grid";

describe("NeonStatsGrid", () => {
  it("renders a stat card per configured entry", () => {
    render(
      <NeonStatsGrid
        cards={[
          { label: "Active Carousels", value: "24" },
          { label: "Published Posts", value: "87" },
        ]}
      />,
    );
    expect(screen.getByText("Active Carousels")).toBeInTheDocument();
    expect(screen.getByText("24")).toBeInTheDocument();
    expect(screen.getByText("Published Posts")).toBeInTheDocument();
  });
});
