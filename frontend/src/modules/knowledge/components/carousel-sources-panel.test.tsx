/**
 * The read-only "Fontes dos carrosséis" tab of the Knowledge Base.
 */
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { API_ENDPOINTS, ROUTE_PATHS } from "@/constants/api";
import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import type { CarouselSourceListResponse } from "@/schemas/knowledge";
import { CarouselSourcesPanel } from "./carousel-sources-panel";

const apiCall = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({
  apiCall,
  apiCallNoContent: vi.fn(),
}));

const labels = en.knowledge.carouselSources;
const CAROUSEL_A = "11111111-1111-1111-1111-111111111111";
const CAROUSEL_B = "22222222-2222-2222-2222-222222222222";

function page(
  overrides: Partial<CarouselSourceListResponse> = {},
): CarouselSourceListResponse {
  return {
    items: [
      {
        id: "s1",
        title: "Artigo da Nature",
        source_type: "url",
        url: "https://example.org/nature",
        project_id: CAROUSEL_A,
        project_title: "IA no trabalho",
        created_at: "2026-10-01T10:00:00Z",
      },
      {
        id: "s2",
        title: "Minhas notas",
        source_type: "note",
        url: null,
        project_id: CAROUSEL_B,
        project_title: "Carreira",
        created_at: "2026-09-30T10:00:00Z",
      },
    ],
    total: 2,
    limit: 20,
    offset: 0,
    carousels: [
      { project_id: CAROUSEL_B, title: "Carreira", count: 1 },
      { project_id: CAROUSEL_A, title: "IA no trabalho", count: 1 },
    ],
    ...overrides,
  };
}

function pageOf(count: number, offset: number, total: number) {
  const [first] = page().items;
  return page({
    items: Array.from({ length: count }, (_, index) => ({
      ...first!,
      id: `s-${offset + index}`,
      title: `Fonte ${offset + index}`,
    })),
    total,
    offset,
  });
}

function renderPanel(): void {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <CarouselSourcesPanel />
    </QueryClientProvider>,
  );
}

function requestedUrl(call: number): string {
  return String(apiCall.mock.calls[call]![0]);
}

describe("CarouselSourcesPanel", () => {
  beforeEach(() => {
    apiCall.mockReset();
  });

  /** Scenario: The carousel sources tab lists each source with its carousel */
  it("lists each source with its type, carousel link and URL", async () => {
    apiCall.mockResolvedValue(page());
    renderPanel();

    expect(await screen.findByText("Artigo da Nature")).toBeInTheDocument();
    expect(screen.getByText("Minhas notas")).toBeInTheDocument();
    expect(screen.getByText(labels.types.url)).toBeInTheDocument();
    expect(screen.getByText(labels.types.note)).toBeInTheDocument();
    expect(
      screen.getByRole("link", {
        name: labels.openCarousel.replace("{title}", "IA no trabalho"),
      }),
    ).toHaveAttribute("href", ROUTE_PATHS.CREATE_WORKSPACE(CAROUSEL_A));
    const sourceLinks = screen.getAllByRole("link", { name: /example\.org/ });
    expect(sourceLinks).toHaveLength(1);
    expect(sourceLinks[0]).toHaveAttribute(
      "href",
      "https://example.org/nature",
    );
    expect(sourceLinks[0]).toHaveAttribute("rel", "noopener noreferrer");
    expect(requestedUrl(0)).toBe(
      `${API_ENDPOINTS.KNOWLEDGE_CAROUSEL_SOURCES}?limit=20&offset=0`,
    );
    expect(pt.knowledge.tabs.carouselSources).toBe("Fontes dos carrosséis");
  });

  /** Scenario: The carousel sources tab lists each source with its carousel */
  it("shows an unknown source type as it is", async () => {
    apiCall.mockResolvedValue(
      page({
        items: [{ ...page().items[1]!, source_type: "podcast" }],
        total: 1,
      }),
    );
    renderPanel();
    expect(await screen.findByText("podcast")).toBeInTheDocument();
  });

  /** Scenario: The carousel sources paginate */
  it("pages forward and back", async () => {
    apiCall.mockResolvedValueOnce(pageOf(20, 0, 25));
    apiCall.mockResolvedValueOnce(pageOf(5, 20, 25));
    apiCall.mockResolvedValue(pageOf(20, 0, 25));
    renderPanel();

    expect(
      await screen.findByText(
        labels.range
          .replace("{from}", "1")
          .replace("{to}", "20")
          .replace("{total}", "25"),
      ),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: labels.previous }),
    ).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: labels.next }));

    expect(
      await screen.findByText(
        labels.range
          .replace("{from}", "21")
          .replace("{to}", "25")
          .replace("{total}", "25"),
      ),
    ).toBeInTheDocument();
    expect(requestedUrl(1)).toContain("offset=20");
    expect(screen.getByRole("button", { name: labels.next })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: labels.previous }));
    await screen.findByText(
      labels.range
        .replace("{from}", "1")
        .replace("{to}", "20")
        .replace("{total}", "25"),
    );
  });

  /** Scenario: The carousel sources can be filtered by carousel */
  it("filters by carousel from the first page", async () => {
    apiCall.mockResolvedValueOnce(pageOf(20, 0, 25));
    apiCall.mockResolvedValueOnce(pageOf(5, 20, 25));
    apiCall.mockResolvedValue(pageOf(1, 0, 1));
    renderPanel();
    await screen.findByText("Fonte 0");
    fireEvent.click(screen.getByRole("button", { name: labels.next }));
    await screen.findByText(/21–/);

    fireEvent.change(screen.getByLabelText(labels.filter), {
      target: { value: CAROUSEL_A },
    });

    await screen.findByText(/1–1/);
    const last = requestedUrl(apiCall.mock.calls.length - 1);
    expect(last).toContain(`project_id=${CAROUSEL_A}`);
    expect(last).toContain("offset=0");
    expect(
      screen.getByRole("option", { name: labels.allCarousels }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("option", { name: "Carreira (1)" }),
    ).toBeInTheDocument();
  });

  /** Scenario: No carousel sources shows an empty state */
  it("says when there are no carousel sources", async () => {
    apiCall.mockResolvedValue(page({ items: [], total: 0, carousels: [] }));
    renderPanel();
    expect(await screen.findByText(labels.empty)).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: labels.next }),
    ).not.toBeInTheDocument();
  });

  /** Scenario: The carousel sources can be filtered by carousel */
  it("hides the pager when the chosen carousel has no sources", async () => {
    apiCall.mockResolvedValueOnce(page());
    apiCall.mockResolvedValue(page({ items: [], total: 0 }));
    renderPanel();
    await screen.findByText("Artigo da Nature");

    fireEvent.change(screen.getByLabelText(labels.filter), {
      target: { value: CAROUSEL_A },
    });

    await screen.findByLabelText(labels.filter);
    await vi.waitFor(() =>
      expect(screen.queryByText("Artigo da Nature")).not.toBeInTheDocument(),
    );
    expect(
      screen.queryByRole("button", { name: labels.next }),
    ).not.toBeInTheDocument();
  });

  /** Scenario: A failed load says so */
  it("says when the sources could not be loaded", async () => {
    apiCall.mockRejectedValue(new Error("boom"));
    renderPanel();
    expect(await screen.findByRole("alert")).toHaveTextContent(labels.error);
  });
});
