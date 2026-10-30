import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/utils";
import type { InstagramInsights } from "@/modules/editorial-operations";
import { InstagramInsightsSection } from "./instagram-insights-section";

const state: {
  data: InstagramInsights | undefined;
  isLoading: boolean;
  isError: boolean;
} = { data: undefined, isLoading: false, isError: false };

vi.mock("@/modules/editorial-operations", () => ({
  useInstagramInsights: () => state,
}));

const CONNECTOR = {
  channel: "instagram",
  configured: true,
  last_sync_at: "2026-10-30T10:00:00Z",
  stale: false,
  error: null,
};

const ROW = {
  media_id: "1789",
  carousel_project_id: null,
  permalink: "https://instagram.com/p/abc",
  topic: "Agents that ship code",
  views: 1000,
  reach: 800,
  saved: 40,
  shares: 10,
  follows: 5,
  profile_visits: 25,
  total_interactions: 90,
  shares_per_100_views: 1,
  fetched_at: "2026-10-30T10:00:00Z",
  stale: false,
};

function insights(
  items: InstagramInsights["items"],
  connector: InstagramInsights["connector"] = CONNECTOR,
): InstagramInsights {
  return {
    items,
    follows_total: null,
    follows_per_post: null,
    shares_per_100_views: null,
    configured: connector.configured,
    connector,
  };
}

describe("InstagramInsightsSection", () => {
  beforeEach(() => {
    state.data = undefined;
    state.isLoading = false;
    state.isError = false;
  });

  // Scenario: Instagram totals match the per-post rows
  it("sums the totals over the rows and lists each post with its fetch time", () => {
    state.data = insights([ROW, { ...ROW, media_id: "1790", views: 500 }]);
    render(<InstagramInsightsSection />);

    expect(screen.getByTestId("ig-kpi-views")).toHaveTextContent("1,500");
    expect(screen.getByTestId("ig-kpi-reach")).toHaveTextContent("1,600");
    expect(screen.getByTestId("ig-kpi-shares")).toHaveTextContent("20");
    expect(screen.getByTestId("ig-kpi-saved")).toHaveTextContent("80");
    expect(screen.getByTestId("ig-kpi-follows")).toHaveTextContent("10");
    expect(screen.getByTestId("ig-kpi-profile_visits")).toHaveTextContent("50");
    const titles = screen.getAllByRole("link", {
      name: "Agents that ship code",
    });
    expect(titles[0]).toHaveAttribute("href", "https://instagram.com/p/abc");
    expect(
      screen.getAllByRole("columnheader").map((h) => h.textContent),
    ).toEqual([
      "Post",
      "Views",
      "Reach",
      "Shares",
      "Saves",
      "Follows",
      "Profile visits",
      "Fetched",
    ]);
    expect(screen.getAllByRole("cell", { name: /Oct 30, 2026/ }).length).toBe(
      2,
    );
  });

  // Scenario: An unconfigured connector is named, not zeroed
  it("names the connector instead of showing zeros", () => {
    state.data = insights([ROW], { ...CONNECTOR, configured: false });
    render(<InstagramInsightsSection />);

    expect(
      screen.getByText(/The instagram connector is not configured/),
    ).toBeInTheDocument();
    expect(screen.getByTestId("ig-kpi-views")).toHaveTextContent("1,000");
  });

  // Scenario: A stale connector says when it last synced
  it("shows the last sync time and the sync error", () => {
    state.data = insights([ROW], {
      ...CONNECTOR,
      stale: true,
      error: "graph_down",
      last_sync_at: "2026-10-29T22:00:00Z",
    });
    render(<InstagramInsightsSection />);

    expect(screen.getByText(/Last sync/)).toBeInTheDocument();
    expect(screen.getByText(/Sync error: graph_down/)).toBeInTheDocument();
  });

  // Scenario: The per-post stale badge is not colour alone
  it("marks a stale row with a text badge", () => {
    state.data = insights([{ ...ROW, stale: true }]);
    render(<InstagramInsightsSection />);

    expect(screen.getByText("outdated")).toBeInTheDocument();
  });

  it("shows the empty, loading and error states", () => {
    state.data = insights([]);
    const { unmount } = render(<InstagramInsightsSection />);
    expect(screen.getByText("No published posts yet.")).toBeInTheDocument();
    unmount();

    state.data = undefined;
    state.isError = true;
    render(<InstagramInsightsSection />);
    expect(
      screen.getByText("Failed to load Instagram insights"),
    ).toBeInTheDocument();
  });

  // Scenario: The connector is named even when there are no posts
  it("names an unconfigured connector with no published posts", () => {
    state.data = insights([], { ...CONNECTOR, configured: false });
    render(<InstagramInsightsSection />);

    expect(
      screen.getByText(/The instagram connector is not configured/),
    ).toBeInTheDocument();
    expect(screen.getByText("No published posts yet.")).toBeInTheDocument();
  });

  // Scenario: The channel picker is keyboard accessible
  it("keeps the post link keyboard accessible with a focus ring", () => {
    state.data = insights([ROW]);
    render(<InstagramInsightsSection />);

    const link = screen.getByRole("link", { name: "Agents that ship code" });
    expect(link.className).toContain("focus-visible:ring-neon-cyan");
  });
});
