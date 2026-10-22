import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import DashboardPage from "./page";

vi.mock("@/modules/editorial-operations", () => ({
  useEditorialAnalytics: () => ({}),
}));
vi.mock("./dashboard-analytics", () => ({
  DashboardAnalyticsStats: () => null,
  DashboardAnalyticsActivity: () => null,
}));
vi.mock("./instagram-insights-card", () => ({
  InstagramInsightsCard: () => null,
}));

describe("dashboard overview headings", () => {
  // Scenario: Dashboard headings keep their order
  it("puts the quick-action titles one level under their section", () => {
    render(<DashboardPage />);
    const levels = screen
      .getAllByRole("heading")
      .map((heading) => Number(heading.tagName.slice(1)));
    expect(levels[0]).toBe(1);
    levels.forEach((level, index) => {
      expect(level - (levels[index - 1] ?? 0)).toBeLessThanOrEqual(1);
    });
    expect(screen.queryAllByRole("heading", { level: 4 })).toHaveLength(0);
  });
});
