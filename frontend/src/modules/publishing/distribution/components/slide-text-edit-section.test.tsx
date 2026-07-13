import { it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { SlideTextEditSection } from "./slide-text-edit-section";
import type { LocalizedSlideReview } from "@/modules/publishing/blog/types-ai";

// AE-0314 — Gherkin: backend/tests/features/carousel_text_edit_no_regen.feature

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock(
  "@/modules/publishing/distribution/hooks/use-edit-carousel-slides",
  () => ({ useEditCarouselSlides: vi.fn() }),
);
vi.mock(
  "@/modules/publishing/distribution/hooks/use-republish-carousel",
  () => ({ useRepublishCarousel: vi.fn() }),
);

import { useEditCarouselSlides } from "@/modules/publishing/distribution/hooks/use-edit-carousel-slides";
import { useRepublishCarousel } from "@/modules/publishing/distribution/hooks/use-republish-carousel";

const republishMutate = vi.fn();

function slides(): LocalizedSlideReview[] {
  return [
    {
      slide_index: 1,
      slide_type: "content",
      presentation_pt: { heading: "titulo", body: "Corpo" },
      presentation_en: { heading: "title", body: "Body" },
    },
  ];
}

function editHook(
  onSuccessData: { validation: { blocking?: boolean } } = {
    validation: { blocking: false },
  },
  isPending = false,
): ReturnType<typeof useEditCarouselSlides> {
  return {
    mutate: (
      _vars: unknown,
      options?: { onSuccess?: (data: unknown) => void },
    ) => options?.onSuccess?.(onSuccessData),
    isPending,
  } as unknown as ReturnType<typeof useEditCarouselSlides>;
}

function republishHook(
  isPending = false,
): ReturnType<typeof useRepublishCarousel> {
  return {
    mutate: republishMutate,
    isPending,
  } as unknown as ReturnType<typeof useRepublishCarousel>;
}

function wrapper() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return function Wrapper({ children }: { children: ReactNode }) {
    return createElement(QueryClientProvider, { client }, children);
  };
}

function renderSection(
  props: Partial<Parameters<typeof SlideTextEditSection>[0]> = {},
): void {
  render(
    createElement(SlideTextEditSection, {
      projectId: "proj-1",
      slides: slides(),
      runInProgress: false,
      onEdited: vi.fn(),
      ...props,
    }),
    { wrapper: wrapper() },
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(useEditCarouselSlides).mockReturnValue(editHook());
  vi.mocked(useRepublishCarousel).mockReturnValue(republishHook());
});

it("blocks editing with a message while a run is in progress", () => {
  renderSection({ runInProgress: true });
  expect(screen.getByText("blockedRunInProgress")).toBeInTheDocument();
  expect(screen.queryByText("editText")).not.toBeInTheDocument();
});

it("states that editing does not regenerate images", () => {
  renderSection();
  expect(screen.getByText("noImageRegen")).toBeInTheDocument();
});

it("saves the edit then chains the republish", async () => {
  const onEdited = vi.fn();
  renderSection({ onEdited });
  await userEvent.click(screen.getByText("editText"));
  const heading = document.querySelector<HTMLTextAreaElement>(
    "#publish-edit-1-presentation_pt-heading",
  );
  fireEvent.change(heading!, { target: { value: "Título Novo" } });
  await userEvent.click(screen.getByText("save"));
  expect(republishMutate).toHaveBeenCalledWith(
    { projectId: "proj-1" },
    expect.objectContaining({ onSuccess: expect.any(Function) }),
  );
});

it("renders the server rejection and does not republish when blocking", async () => {
  vi.mocked(useEditCarouselSlides).mockReturnValue(
    editHook({ validation: { blocking: true } }),
  );
  renderSection();
  await userEvent.click(screen.getByText("editText"));
  const heading = document.querySelector<HTMLTextAreaElement>(
    "#publish-edit-1-presentation_pt-heading",
  );
  fireEvent.change(heading!, { target: { value: "over budget" } });
  await userEvent.click(screen.getByText("save"));
  expect(screen.getByText("blockingViolations")).toBeInTheDocument();
  expect(republishMutate).not.toHaveBeenCalled();
});

it("shows the PDF rebuild pending state when the marker is set", () => {
  renderSection({ rebuildPending: true });
  expect(screen.getByText("rebuildPending")).toBeInTheDocument();
});
