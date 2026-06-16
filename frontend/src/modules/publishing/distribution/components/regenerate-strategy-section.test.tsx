import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { RegenerateStrategySection } from "./regenerate-strategy-section";
import type { CarouselProjectResponse } from "@/schemas/carousel";

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => {
    const entries: Record<string, string> = {
      title: "Slide Layout",
      selectTemplate: "Select a template style for your slides:",
      loading: "Loading layout options…",
      regenerate: "Regenerate slides",
      regenerating: "Regenerating…",
      success: "Slides regenerated with new layout.",
      fetchError: "Could not load layout options.",
      retry: "Retry",
    };
    return (key: string) => entries[key] ?? key;
  }),
}));

vi.mock("@/modules/editorial", () => ({
  useAvailableStrategies: vi.fn(),
  useRegenerateSlides: vi.fn(),
}));

import {
  useAvailableStrategies,
  useRegenerateSlides,
} from "@/modules/editorial";

const mockStrategiesData = {
  strategies: [
    { name: "stat_card_grid", display_name: "Stat Card Grid" },
    { name: "feature_grid", display_name: "Feature Card Grid" },
    { name: "intro_hero", display_name: "Intro Hero" },
  ],
};

function buildProject(
  overrides?: Partial<CarouselProjectResponse>,
): CarouselProjectResponse {
  return {
    id: "proj-1",
    topic: "AI Testing",
    audience: "Devs",
    niche: "ML",
    title: "Title",
    subtitle: null,
    theme: "auto",
    status: "completed",
    blog_markdown: null,
    blog_translations: null,
    caption: null,
    design_tokens: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    slide_layout_strategy: "feature_grid",
    ...overrides,
  };
}

const mockMutate = vi.fn();

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
    },
  });
}

function createWrapper(queryClient = createQueryClient()) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(
      QueryClientProvider,
      { client: queryClient },
      children,
    );
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useRegenerateSlides).mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isError: false,
    error: null,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useRegenerateSlides>);
});

it("shows loading spinner while strategies are loading", () => {
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAvailableStrategies>);

  render(
    createElement(RegenerateStrategySection, {
      project: buildProject(),
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  expect(screen.getByText("Loading layout options…")).toBeInTheDocument();
});

it("shows error state with retry button when fetch fails", async () => {
  const refetchMock = vi.fn();
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: true,
    refetch: refetchMock,
  } as unknown as ReturnType<typeof useAvailableStrategies>);

  render(
    createElement(RegenerateStrategySection, {
      project: buildProject(),
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  expect(
    screen.getByText("Could not load layout options."),
  ).toBeInTheDocument();
  const retryButton = screen.getByText("Retry");
  await userEvent.click(retryButton);
  expect(refetchMock).toHaveBeenCalledTimes(1);
});

it("renders template grid with all 6 templates", () => {
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: mockStrategiesData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAvailableStrategies>);

  render(
    createElement(RegenerateStrategySection, {
      project: buildProject(),
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  expect(screen.getByText("Analysis")).toBeInTheDocument();
  expect(screen.getByText("Comparison")).toBeInTheDocument();
  expect(screen.getByText("Tutorial")).toBeInTheDocument();
  expect(screen.getByText("News Flash")).toBeInTheDocument();
  expect(screen.getByText("Deep Dive")).toBeInTheDocument();
  expect(screen.getByText("Listicle")).toBeInTheDocument();
});

it("highlights the template matching the project's slide_layout_strategy", () => {
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: mockStrategiesData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAvailableStrategies>);

  const project = buildProject({ slide_layout_strategy: "feature_grid" });

  render(
    createElement(RegenerateStrategySection, {
      project,
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  const comparisonCard = screen
    .getByText("Comparison")
    .closest("[role='button']");
  expect(comparisonCard).toBeTruthy();
});

it("disables regenerate button while mutation is in-flight", () => {
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: mockStrategiesData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAvailableStrategies>);
  vi.mocked(useRegenerateSlides).mockReturnValue({
    mutate: mockMutate,
    isPending: true,
    isError: false,
    error: null,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useRegenerateSlides>);

  render(
    createElement(RegenerateStrategySection, {
      project: buildProject(),
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  const button = screen.getByText("Regenerating…");
  expect(button).toBeDisabled();
});

it("calls regenerate mutation with selected strategy", async () => {
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: mockStrategiesData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAvailableStrategies>);

  render(
    createElement(RegenerateStrategySection, {
      project: buildProject({ slide_layout_strategy: "stat_card_grid" }),
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  const button = screen.getByText("Regenerate slides");
  await userEvent.click(button);

  expect(mockMutate).toHaveBeenCalledWith(
    { projectId: "proj-1", strategy: "stat_card_grid" },
    expect.objectContaining({ onSuccess: expect.any(Function) }),
  );
});

it("shows error message when mutation fails", () => {
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: mockStrategiesData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAvailableStrategies>);
  vi.mocked(useRegenerateSlides).mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isError: true,
    error: new Error("Strategy not found"),
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useRegenerateSlides>);

  render(
    createElement(RegenerateStrategySection, {
      project: buildProject(),
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  expect(screen.getByText("Strategy not found")).toBeInTheDocument();
});

it("defaults to first template when no slide_layout_strategy is set", () => {
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: mockStrategiesData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAvailableStrategies>);

  render(
    createElement(RegenerateStrategySection, {
      project: buildProject({ slide_layout_strategy: null }),
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  const analysisCard = screen.getByText("Analysis").closest("[role='button']");
  expect(analysisCard).toBeTruthy();
});

it("shows success message after successful regeneration", async () => {
  vi.mocked(useAvailableStrategies).mockReturnValue({
    data: mockStrategiesData,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useAvailableStrategies>);
  vi.mocked(useRegenerateSlides).mockReturnValue({
    mutate: (_vars: unknown, options?: { onSuccess?: () => void }) => {
      options?.onSuccess?.();
    },
    isPending: false,
    isError: false,
    error: null,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useRegenerateSlides>);

  render(
    createElement(RegenerateStrategySection, {
      project: buildProject(),
      projectId: "proj-1",
    }),
    { wrapper: createWrapper() },
  );

  const button = screen.getByText("Regenerate slides");
  await userEvent.click(button);

  expect(
    screen.getByText("Slides regenerated with new layout."),
  ).toBeInTheDocument();
});
