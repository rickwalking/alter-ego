import { render as renderBare, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import en from "@/i18n/locales/en.json";
import type { EditorialAnalyticsSummary } from "@/modules/editorial-operations";
import AnalyticsPage from "./page";

vi.mock("next-intl", async (importOriginal) => importOriginal());

const m = vi.hoisted(() => ({
  summary: null as EditorialAnalyticsSummary | null,
}));

vi.mock("@/modules/editorial-operations", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/editorial-operations")>()),
  useEditorialAnalytics: () => ({
    data: { summary: m.summary, velocity_by_week: [] },
    loading: false,
    error: null,
    disabled: false,
    refetch: vi.fn(),
  }),
  useInstagramInsights: () => ({
    data: null,
    isLoading: false,
    isError: false,
  }),
}));

function render(ui: React.ReactElement): ReturnType<typeof renderBare> {
  return renderBare(ui, {
    wrapper: ({ children }) => (
      <NextIntlClientProvider locale="en" messages={en} timeZone="UTC">
        {children}
      </NextIntlClientProvider>
    ),
  });
}

function summary(
  average: number | null,
  count: number,
): EditorialAnalyticsSummary {
  return {
    total_posts: 4,
    published_this_week: 1,
    published_this_month: 2,
    content_velocity_per_week: 1,
    status_breakdown: { published: 2, draft: 2 },
    channels: [
      {
        channel: "blog",
        published_total: 2,
        published_this_week: 1,
        published_this_month: 1,
      },
      {
        channel: "carousel",
        published_total: 2,
        published_this_week: 0,
        published_this_month: 1,
      },
    ],
    pending_review: 0,
    draft_count: 2,
    quality_score_average: average,
    quality_score_count: count,
  };
}

describe("AnalyticsPage quality score (AE-0497)", () => {
  it("says there is no data without content scores", () => {
    // Scenario: Without content scores the tile says there is no data
    m.summary = summary(null, 0);
    render(<AnalyticsPage />);
    expect(screen.getByText("No data")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  it("shows the average and the count behind it", () => {
    // Scenario: With content scores the tile shows the average and the count
    m.summary = summary(70.5, 2);
    render(<AnalyticsPage />);
    expect(screen.getByText("70.5%")).toBeInTheDocument();
    expect(screen.getByText("2 evaluations")).toBeInTheDocument();
  });

  it("uses the singular for one score", () => {
    // Scenario: With content scores the tile shows the average and the count
    m.summary = summary(90, 1);
    render(<AnalyticsPage />);
    expect(screen.getByText("1 evaluation")).toBeInTheDocument();
  });
});
