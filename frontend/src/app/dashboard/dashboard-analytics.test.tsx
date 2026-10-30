import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@/test/utils";
import type { EditorialAnalyticsState } from "@/modules/editorial-operations";
import {
  DashboardAnalyticsActivity,
  DashboardAnalyticsStats,
} from "./dashboard-analytics";

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
          channels: [
            {
              channel: "blog",
              published_total: 12,
              published_this_week: 2,
              published_this_month: 5,
            },
            {
              channel: "carousel",
              published_total: 3,
              published_this_week: 0,
              published_this_month: 1,
            },
          ],
          pending_review: 3,
          draft_count: 4,
          quality_score_average: 81,
          quality_score_count: 3,
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
    // Scenario: With content scores the tile shows the average and the count
    expect(screen.getByText("81%")).toBeInTheDocument();
    expect(screen.getByText("in review")).toBeInTheDocument();
  });

  it("says there is no data without a quality score", () => {
    // Scenario: Without content scores the tile says there is no data
    const state = analytics({
      data: {
        summary: {
          total_posts: 2,
          published_this_week: 1,
          published_this_month: 1,
          content_velocity_per_week: 1,
          status_breakdown: { published: 2 },
          channels: [
            {
              channel: "blog",
              published_total: 12,
              published_this_week: 2,
              published_this_month: 5,
            },
            {
              channel: "carousel",
              published_total: 3,
              published_this_week: 0,
              published_this_month: 1,
            },
          ],
          pending_review: 0,
          draft_count: 0,
          quality_score_average: null,
          quality_score_count: 0,
        },
        velocity_by_week: [],
      },
    });
    render(<DashboardAnalyticsStats state={state} />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.queryByText(/%$/)).toBeNull();
  });

  it("renders no activity lists without data", () => {
    const { container } = render(
      <DashboardAnalyticsActivity state={analytics()} />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
