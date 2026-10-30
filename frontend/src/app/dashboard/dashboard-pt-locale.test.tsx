import { render as renderBare, screen } from "@testing-library/react";
import { NextIntlClientProvider } from "next-intl";
import { describe, expect, it, vi } from "vitest";

import pt from "@/i18n/locales/pt.json";

import { buildCalendarDaysFromApi } from "@/modules/editorial-operations";
import type { CalendarItem } from "@/modules/editorial";
import type {
  EditorialAnalyticsState,
  EditorialAnalyticsSummary,
} from "@/modules/editorial-operations";

vi.mock("next-intl", async (importOriginal) => importOriginal());
vi.mock("@/modules/editorial-operations", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/editorial-operations")>()),
  useEditorialAnalytics: () => ANALYTICS,
}));
vi.mock("./instagram-insights-card", () => ({
  InstagramInsightsCard: () => null,
}));
vi.mock("./analytics/instagram-insights-section", () => ({
  InstagramInsightsSection: () => null,
}));

import DashboardPage from "./page";
import AnalyticsPage from "./analytics/page";
import { CalendarGrid } from "./calendar/calendar-grid";
import { CalendarLegend } from "./calendar/calendar-legend";
import {
  DashboardAnalyticsActivity,
  DashboardAnalyticsStats,
} from "./dashboard-analytics";

function render(ui: React.ReactElement): ReturnType<typeof renderBare> {
  return renderBare(ui, {
    wrapper: ({ children }) => (
      <NextIntlClientProvider
        locale="pt"
        messages={pt}
        timeZone="America/Sao_Paulo"
      >
        {children}
      </NextIntlClientProvider>
    ),
  });
}

const SUMMARY: EditorialAnalyticsSummary = {
  total_posts: 26,
  published_this_week: 0,
  published_this_month: 0,
  content_velocity_per_week: 0,
  status_breakdown: { draft: 26 },
  channels: [],
  pending_review: 0,
  draft_count: 26,
  quality_score_average: null,
  quality_score_count: 0,
};

const ANALYTICS: EditorialAnalyticsState = {
  data: {
    summary: SUMMARY,
    velocity_by_week: [],
  },
  loading: false,
  error: null,
  disabled: false,
  refetch: vi.fn(),
};

const ENGLISH_LEFTOVERS = [
  "overview",
  "New Carousel",
  "Write Blog Post",
  "Open Chat",
  "26 items",
  "Live",
  "Drafts",
  "26 in progress",
  "Today",
  "Weekly velocity",
  "Trend",
];

describe("dashboard in Portuguese", () => {
  // Scenario: The dashboard overview is fully translated
  it("shows the overview in Portuguese only", () => {
    render(<DashboardPage />);
    for (const english of ENGLISH_LEFTOVERS) {
      expect(screen.queryByText(english)).not.toBeInTheDocument();
    }
    expect(screen.getByText("Novo carrossel")).toBeInTheDocument();
    expect(screen.getByText("Escrever post")).toBeInTheDocument();
    expect(screen.getByText("Abrir chat")).toBeInTheDocument();
    expect(screen.getByText("visão geral")).toBeInTheDocument();
    expect(screen.getByText("26 itens")).toBeInTheDocument();
    expect(screen.getByText("Rascunho")).toBeInTheDocument();
    expect(screen.getByText("26 em andamento")).toBeInTheDocument();
    expect(screen.getByText("0 posts/semana")).toBeInTheDocument();
    // Scenario: Without content scores the tile says there is no data
    expect(screen.getByText("Sem dados")).toBeInTheDocument();
    expect(screen.queryByText("0%")).not.toBeInTheDocument();
  });

  // Scenario: With content scores the tile shows the average and the count
  it("shows the quality score with its count in Portuguese", () => {
    render(
      <DashboardAnalyticsStats
        state={{
          ...ANALYTICS,
          data: {
            summary: {
              ...SUMMARY,
              quality_score_average: 70.5,
              quality_score_count: 2,
            },
            velocity_by_week: [],
          },
        }}
      />,
    );
    expect(screen.getByText("70.5%")).toBeInTheDocument();
    expect(screen.getByText("2 avaliações")).toBeInTheDocument();
  });

  // Scenario: Activity counts use the singular for one item
  it("uses the singular for a count of one", () => {
    render(
      <DashboardAnalyticsActivity
        state={{
          ...ANALYTICS,
          data: {
            summary: {
              ...SUMMARY,
              content_velocity_per_week: 1,
              status_breakdown: { draft: 1 },
            },
            velocity_by_week: [],
          },
        }}
      />,
    );
    expect(screen.getByText("1 item")).toBeInTheDocument();
    expect(screen.getByText("1 post/semana")).toBeInTheDocument();
  });

  // Scenario: The calendar legend, chips and empty month are translated
  it("shows the calendar legend, chips and empty month in Portuguese", () => {
    const item: CalendarItem = {
      id: "1",
      content_type: "carousel",
      title: "Opinião impopular",
      status: "approved",
      event_date: "2026-10-15",
      phase_status: "approved",
    };
    const { unmount } = render(
      <>
        <CalendarGrid
          label="outubro de 2026"
          days={buildCalendarDaysFromApi(new Date(2026, 9, 1), [item], null)}
        />
        <CalendarLegend />
      </>,
    );
    expect(screen.getByText("carrossel")).toBeInTheDocument();
    expect(screen.getByText("aprovado")).toBeInTheDocument();
    for (const label of [
      "Carrossel",
      "Post do blog",
      "Rascunho",
      "Reunião",
      "Revisão",
      "Publicado",
    ]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    unmount();
    render(
      <CalendarGrid
        label="outubro de 2026"
        days={buildCalendarDaysFromApi(new Date(2026, 9, 1), [], null).map(
          (day) => ({
            ...day,
            cur: false,
          }),
        )}
      />,
    );
    expect(
      screen.getByText("Nenhum conteúdo agendado neste mês"),
    ).toBeInTheDocument();
  });

  // Scenario: The analytics breadcrumb is translated
  it("shows the analytics breadcrumb in Portuguese", () => {
    render(<AnalyticsPage />);
    expect(screen.getByText("análises")).toBeInTheDocument();
    expect(screen.queryByText("analytics")).not.toBeInTheDocument();
  });
});
