import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { RebuildPdfSection } from "./rebuild-pdf-section";

// Scenario: Publish page "Rebuild PDF" action (see
// backend/tests/features/carousel_republish.feature).

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => {
    const entries: Record<string, string> = {
      title: "Rebuild PDF",
      description: "Re-render the slides and PDF.",
      rebuild: "Rebuild PDF",
      rebuilding: "Rebuilding…",
      confirmTitle: "Rebuild the PDF?",
      confirmBody: "This re-renders every slide and PDF.",
      confirm: "Rebuild",
      cancel: "Cancel",
      success: "PDF rebuilt with the latest slide text.",
      failed: "Could not rebuild the PDF.",
    };
    return (key: string) => entries[key] ?? key;
  }),
}));

vi.mock(
  "@/modules/publishing/distribution/hooks/use-republish-carousel",
  () => ({
    useRepublishCarousel: vi.fn(),
  }),
);

import { useRepublishCarousel } from "@/modules/publishing/distribution/hooks/use-republish-carousel";

const mockMutate = vi.fn();

function baseHook(): ReturnType<typeof useRepublishCarousel> {
  return {
    mutate: mockMutate,
    isPending: false,
    isError: false,
    error: null,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useRepublishCarousel>;
}

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: Infinity } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children);
  };
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useRepublishCarousel).mockReturnValue(baseHook());
});

it("opens the confirmation dialog when Rebuild PDF is clicked", async () => {
  render(
    createElement(RebuildPdfSection, {
      projectId: "proj-1",
      onRebuilt: vi.fn(),
    }),
    { wrapper: wrapper() },
  );

  await userEvent.click(
    screen.getByText("Rebuild PDF", { selector: "button" }),
  );

  expect(
    screen.getByText("This re-renders every slide and PDF."),
  ).toBeVisible();
});

it("calls the republish mutation on confirm", async () => {
  render(
    createElement(RebuildPdfSection, {
      projectId: "proj-1",
      onRebuilt: vi.fn(),
    }),
    { wrapper: wrapper() },
  );

  await userEvent.click(
    screen.getByText("Rebuild PDF", { selector: "button" }),
  );
  await userEvent.click(screen.getByText("Rebuild"));

  expect(mockMutate).toHaveBeenCalledWith(
    { projectId: "proj-1" },
    expect.objectContaining({ onSuccess: expect.any(Function) }),
  );
});

it("busts the cache and shows success on a rebuilt version", async () => {
  const onRebuilt = vi.fn();
  vi.mocked(useRepublishCarousel).mockReturnValue({
    mutate: (
      _vars: unknown,
      options?: { onSuccess?: (data: { artifact_version: string }) => void },
    ) => {
      options?.onSuccess?.({ artifact_version: "sha256-new" });
    },
    isPending: false,
    isError: false,
    error: null,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useRepublishCarousel>);

  render(
    createElement(RebuildPdfSection, {
      projectId: "proj-1",
      onRebuilt,
    }),
    { wrapper: wrapper() },
  );

  await userEvent.click(
    screen.getByText("Rebuild PDF", { selector: "button" }),
  );
  await userEvent.click(screen.getByText("Rebuild"));

  expect(onRebuilt).toHaveBeenCalledWith("sha256-new");
  expect(
    screen.getByText("PDF rebuilt with the latest slide text."),
  ).toBeInTheDocument();
});

it("shows an error message when the rebuild fails", () => {
  vi.mocked(useRepublishCarousel).mockReturnValue({
    mutate: mockMutate,
    isPending: false,
    isError: true,
    error: new Error("An artifact build is already running for this carousel."),
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useRepublishCarousel>);

  render(
    createElement(RebuildPdfSection, {
      projectId: "proj-1",
      onRebuilt: vi.fn(),
    }),
    { wrapper: wrapper() },
  );

  expect(
    screen.getByText("An artifact build is already running for this carousel."),
  ).toBeInTheDocument();
});
