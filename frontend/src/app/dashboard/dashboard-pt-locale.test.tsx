import { render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { buildCalendarDaysFromApi } from "@/modules/editorial-operations";
import type { CalendarItem } from "@/modules/editorial";
import type { EditorialAnalyticsState } from "@/modules/editorial-operations";

vi.mock("next-intl", async () => {
  const pt = (await import("@/i18n/locales/pt.json")).default;
  const lookup = (path: string): unknown =>
    path
      .split(".")
      .reduce<unknown>(
        (node, key) =>
          node && typeof node === "object"
            ? (node as Record<string, unknown>)[key]
            : undefined,
        pt,
      );
  return {
    useLocale: () => "pt",
    useTranslations:
      (namespace?: string) =>
      (key: string, values?: Record<string, string | number>): string => {
        const raw = lookup(namespace ? `${namespace}.${key}` : key);
        if (typeof raw !== "string") return key;
        return raw.replace(/\{(\w+)\}/g, (_, token: string) =>
          String(values?.[token] ?? token),
        );
      },
  };
});
vi.mock("@/modules/editorial-operations", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/modules/editorial-operations")>()),
  useEditorialAnalytics: () => ANALYTICS,
}));
vi.mock("./instagram-insights-card", () => ({
  InstagramInsightsCard: () => null,
}));

import DashboardPage from "./page";
import AnalyticsPage from "./analytics/page";
import { CalendarGrid } from "./calendar/calendar-grid";
import { CalendarLegend } from "./calendar/calendar-legend";

const ANALYTICS: EditorialAnalyticsState = {
  data: {
    summary: {
      total_posts: 26,
      published_this_week: 0,
      published_this_month: 0,
      content_velocity_per_week: 0,
      status_breakdown: { draft: 26 },
      average_views: 0,
      pending_review: 0,
      draft_count: 26,
      quality_score_average: 0,
    },
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
          days={buildCalendarDaysFromApi(new Date(2026, 9, 1), [item])}
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
        days={buildCalendarDaysFromApi(new Date(2026, 9, 1), []).map((day) => ({
          ...day,
          cur: false,
        }))}
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
