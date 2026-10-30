import {
  fireEvent,
  render as renderBare,
  screen,
} from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";
import en from "@/i18n/locales/en.json";
import type {
  AnalyticsVelocityWeek,
  EditorialAnalyticsSummary,
} from "@/modules/editorial-operations";
import AnalyticsPage from "./page";

vi.mock("next-intl", async (importOriginal) => importOriginal());

const SUMMARY: EditorialAnalyticsSummary = {
  total_posts: 7,
  published_this_week: 3,
  published_this_month: 5,
  content_velocity_per_week: 3,
  status_breakdown: { published: 7 },
  channels: [
    {
      channel: "blog",
      published_total: 5,
      published_this_week: 1,
      published_this_month: 2,
    },
    {
      channel: "carousel",
      published_total: 2,
      published_this_week: 2,
      published_this_month: 3,
    },
  ],
  pending_review: 0,
  draft_count: 0,
  quality_score_average: null,
  quality_score_count: 0,
};

const WEEKS: AnalyticsVelocityWeek[] = [
  {
    week_start: "2026-10-16",
    published_count: 0,
    channels: { blog: 0, carousel: 0 },
  },
  {
    week_start: "2026-10-23",
    published_count: 3,
    channels: { blog: 1, carousel: 2 },
  },
];

vi.mock("@/modules/editorial-operations", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/editorial-operations")>()),
  useEditorialAnalytics: () => ({
    data: { summary: SUMMARY, velocity_by_week: WEEKS },
    loading: false,
    error: null,
    disabled: false,
    refetch: vi.fn(),
  }),
  useInstagramInsights: () => ({
    data: undefined,
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

describe("AnalyticsPage channels (AE-0500)", () => {
  // Scenario: The velocity chart switches between channels
  it("lists the channel picker and filters the bars per channel", () => {
    render(<AnalyticsPage />);

    expect(
      screen.getByText("Published — Blog: 5, Carousels: 2"),
    ).toBeInTheDocument();

    const picker = screen.getByRole("group", { name: "Velocity channel" });
    const all = screen.getByRole("button", { name: "All" });
    const blog = screen.getByRole("button", { name: "Blog" });
    const carousels = screen.getByRole("button", { name: "Carousels" });
    expect(picker).toContainElement(all);
    expect(all).toHaveAttribute("aria-pressed", "true");

    const weekRow = screen.getByText("2026-10-23").parentElement;
    expect(weekRow).toHaveTextContent("3");

    fireEvent.click(blog);
    expect(blog).toHaveAttribute("aria-pressed", "true");
    expect(screen.getByText("2026-10-23").parentElement).toHaveTextContent("1");

    fireEvent.click(carousels);
    expect(screen.getByText("2026-10-23").parentElement).toHaveTextContent("2");
  });

  // Scenario: The channel picker is keyboard accessible
  it("exposes every channel option as a focusable button with a focus ring", () => {
    render(<AnalyticsPage />);

    for (const name of ["All", "Blog", "Carousels"]) {
      const button = screen.getByRole("button", { name });
      expect(button.tagName).toBe("BUTTON");
      expect(button.className).toContain("focus-visible:ring-neon-cyan");
    }
  });
});
