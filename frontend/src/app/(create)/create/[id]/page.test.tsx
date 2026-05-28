import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

// Feature: carousel_editorial_consolidation.feature — Create workspace uses editorial workflow only

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("@/features/create/hooks", () => ({
  useCarouselProject: vi.fn(),
}));

vi.mock("@/features/create/hooks/use-editorial-workflow", () => ({
  useEditorialWorkflow: vi.fn(),
}));

vi.mock("@/features/chat/hooks/use-chat", () => ({
  useCreateConversation: vi.fn(),
}));

vi.mock("@/features/create/components/editorial-workflow-panel", () => ({
  EditorialWorkflowPanel: () => null,
}));

vi.mock("@/features/create/components/source-material-viewer", () => ({
  SourceMaterialViewer: () => null,
}));

import { useParams } from "next/navigation";
import { useCarouselProject } from "@/features/create/hooks";
import { useEditorialWorkflow } from "@/features/create/hooks/use-editorial-workflow";
import { useCreateConversation } from "@/features/chat/hooks/use-chat";
import WorkspacePage from "./page";

const mockUseParams = vi.mocked(useParams);
const mockUseCarouselProject = vi.mocked(useCarouselProject);
const mockUseEditorialWorkflow = vi.mocked(useEditorialWorkflow);
const mockUseCreateConversation = vi.mocked(useCreateConversation);

function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
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

  mockUseParams.mockReturnValue({ id: "test-project-id" });
  mockUseCarouselProject.mockReturnValue({
    data: {
      id: "test-project-id",
      topic: "Test Topic",
      audience: "Devs",
      niche: "Tech",
      title: null,
      subtitle: null,
      theme: "developer_skills",
      status: "pending",
      blog_markdown: null,
      blog_translations: null,
      caption: null,
      design_tokens: null,
      created_at: "2026-04-20T00:00:00Z",
      updated_at: "2026-04-20T00:00:00Z",
    },
    isLoading: false,
  } as ReturnType<typeof useCarouselProject>);
  mockUseEditorialWorkflow.mockReturnValue({
    state: null,
    phaseEvents: [],
    loading: false,
    error: null,
    hasActiveWorkflow: false,
    transportMode: "sse",
    start: vi.fn(),
    resume: vi.fn(),
    refreshState: vi.fn(),
    approve: vi.fn(),
    revise: vi.fn(),
    awaitingHumanReview: false,
  });
  mockUseCreateConversation.mockReturnValue({
    mutateAsync: vi.fn(() => new Promise(() => undefined)),
  } as unknown as ReturnType<typeof useCreateConversation>);
});

afterEach(() => {
  sessionStorage.clear();
});

describe("WorkspacePage", () => {
  it("renders the workspace title", () => {
    render(<WorkspacePage />, { wrapper: createWrapper() });
    expect(screen.getByText(/workspace\.title/)).toBeInTheDocument();
  });

  it("subscribes to editorial workflow for the project", () => {
    render(<WorkspacePage />, { wrapper: createWrapper() });
    expect(mockUseEditorialWorkflow).toHaveBeenCalledWith("test-project-id");
  });

  it("shows brief materials gate before workflow starts", () => {
    render(<WorkspacePage />, { wrapper: createWrapper() });
    expect(screen.getByText("title")).toBeInTheDocument();
  });
});
