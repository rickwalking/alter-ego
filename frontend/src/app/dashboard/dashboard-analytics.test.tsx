import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/utils";
import type { EditorialAnalyticsState } from "@/modules/editorial-operations";
import {
  DashboardAnalyticsActivity,
  DashboardAnalyticsStats,
} from "./dashboard-analytics";

// Gherkin: backend/tests/features/instagram_insights.feature (AE-0378)
function analytics(
  overrides: Partial<EditorialAnalyticsState> = {},
): EditorialAnalyticsState {
  return {
    data: null,
    loading: false,
    error: null,
    disabled: false,
    refetch: vi.fn(),
    ...overrides,
  };
}

describe("DashboardAnalyticsStats", () => {
  // Scenario: Analytics flag off
  it("shows the disabled state instead of an error", () => {
    render(<DashboardAnalyticsStats state={analytics({ disabled: true })} />);
    expect(screen.getByTestId("analytics-disabled")).toBeInTheDocument();
    expect(screen.getByText("Editorial analytics is off")).toBeInTheDocument();
    expect(
      screen.queryByText("Failed to load analytics"),
    ).not.toBeInTheDocument();
  });

  it("keeps the inline error for a real failure", () => {
    render(<DashboardAnalyticsStats state={analytics({ error: "boom" })} />);
    expect(screen.getByText("Failed to load analytics")).toBeInTheDocument();
  });

  it("renders the stats and the activity lists with data", () => {
    const state = analytics({
      data: {
        summary: {
          total_posts: 12,
          published_this_week: 2,
          published_this_month: 5,
          content_velocity_per_week: 1.5,
          status_breakdown: { in_review: 3 },
          average_views: 0,
          pending_review: 3,
          draft_count: 4,
          quality_score_average: 81,
        },
        velocity_by_week: [],
      },
    });
    render(
      <>
        <DashboardAnalyticsStats state={state} />
        <DashboardAnalyticsActivity state={state} />
      </>,
    );
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByText("81%")).toBeInTheDocument();
    expect(screen.getByText("in review")).toBeInTheDocument();
  });

  it("renders no activity lists without data", () => {
    const { container } = render(
      <DashboardAnalyticsActivity state={analytics()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
