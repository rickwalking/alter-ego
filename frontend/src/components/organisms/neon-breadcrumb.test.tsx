import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { NeonBreadcrumb } from "@/components/organisms/neon-breadcrumb";

describe("NeonBreadcrumb", () => {
  /** Scenario: The breadcrumb links back to the board */
  it("renders items with a link as real links", () => {
    render(
      <NeonBreadcrumb
        items={[
          { label: "projects", href: "/dashboard/workflow" },
          { label: "Tópico" },
        ]}
      />,
    );
    const link = screen.getByRole("link", { name: "projects" });
    expect(link).toHaveAttribute("href", "/dashboard/workflow");
    expect(link.className).toContain("focus-visible:ring-neon-cyan");
  });

  /** Scenario: The breadcrumb links back to the board */
  it("keeps the current item as plain text", () => {
    render(
      <NeonBreadcrumb
        items={[
          { label: "projects", href: "/dashboard/workflow" },
          { label: "Tópico" },
        ]}
      />,
    );
    expect(screen.queryByRole("link", { name: "Tópico" })).toBeNull();
    expect(screen.getByText("Tópico")).toBeInTheDocument();
  });

  it("renders plain items without links when no href is passed", () => {
    render(<NeonBreadcrumb items={[{ label: "pipeline" }]} />);
    expect(screen.queryByRole("link")).toBeNull();
    expect(screen.getByText("pipeline")).toBeInTheDocument();
  });
});
