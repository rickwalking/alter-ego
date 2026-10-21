import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/utils";
import type { InstagramInsights } from "@/modules/editorial-operations";
import { InstagramInsightsCard } from "./instagram-insights-card";

const state: {
  data: InstagramInsights | undefined;
  isLoading: boolean;
  isError: boolean;
} = { data: undefined, isLoading: false, isError: false };

vi.mock("@/modules/editorial-operations", () => ({
  useInstagramInsights: () => state,
}));

const ROW = {
  media_id: "1789",
  carousel_project_id: null,
  permalink: null,
  topic: "Agents that ship code",
  views: 1000,
  reach: 800,
  saved: 40,
  shares: 10,
  follows: null,
  profile_visits: 25,
  total_interactions: 90,
  shares_per_100_views: 1,
  fetched_at: "2026-10-20T12:00:00Z",
  stale: true,
};

describe("InstagramInsightsCard", () => {
  beforeEach(() => {
    state.data = undefined;
    state.isLoading = false;
    state.isError = false;
  });

  // Scenario: Missing metric
  it("shows totals, ratios and n/a for a missing metric", () => {
    state.data = {
      items: [ROW],
      follows_total: null,
      follows_per_post: null,
      shares_per_100_views: 1,
      configured: true,
    };
    render(<InstagramInsightsCard />);
    expect(screen.getByTestId("ig-kpi-views")).toHaveTextContent("1,000");
    expect(screen.getByTestId("ig-kpi-follows")).toHaveTextContent("n/a");
    expect(screen.getByTestId("ig-kpi-followsPerPost")).toHaveTextContent(
      "n/a",
    );
    expect(screen.getByTestId("ig-kpi-sharesPer100Views")).toHaveTextContent(
      "1",
    );
    expect(screen.getByText("Agents that ship code")).toBeInTheDocument();
    expect(screen.getByText("outdated")).toBeInTheDocument();
  });

  // Scenario: No Instagram account configured
  it("says when no account is configured", () => {
    state.data = {
      items: [ROW],
      follows_total: null,
      follows_per_post: null,
      shares_per_100_views: null,
      configured: false,
    };
    render(<InstagramInsightsCard />);
    expect(
      screen.getByText(/No Instagram account is configured/),
    ).toBeInTheDocument();
  });

  it("shows the empty and error states", () => {
    state.data = {
      items: [],
      follows_total: null,
      follows_per_post: null,
      shares_per_100_views: null,
      configured: true,
    };
    const { unmount } = render(<InstagramInsightsCard />);
    expect(screen.getByText("No published posts yet.")).toBeInTheDocument();
    unmount();
    state.data = undefined;
    state.isError = true;
    render(<InstagramInsightsCard />);
    expect(
      screen.getByText("Failed to load Instagram insights"),
    ).toBeInTheDocument();
  });
});
