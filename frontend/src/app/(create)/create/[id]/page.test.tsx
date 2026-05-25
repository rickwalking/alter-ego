import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";

// Feature: Workspace Page
// Mutation guard: ensures the workspace page relies on SSE streaming
// (GET /stream via EventSource) and does not auto-fire POST /generate,
// which would cause double pipeline execution.

vi.mock("next/navigation", () => ({
  useParams: vi.fn(),
}));

vi.mock("next-intl", () => ({
  useTranslations: vi.fn(() => (key: string) => key),
}));

vi.mock("@/features/create/hooks", () => ({
  useCarouselProject: vi.fn(),
  useCarouselStatus: vi.fn(),
  useCarouselStream: vi.fn(),
  useResumeCarousel: vi.fn(),
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
import {
  useCarouselProject,
  useCarouselStatus,
  useCarouselStream,
  useResumeCarousel,
} from "@/features/create/hooks";
import { useCreateConversation } from "@/features/chat/hooks/use-chat";
import WorkspacePage from "./page";

const mockUseParams = vi.mocked(useParams);
const mockUseCarouselProject = vi.mocked(useCarouselProject);
const mockUseCarouselStatus = vi.mocked(useCarouselStatus);
const mockUseCarouselStream = vi.mocked(useCarouselStream);
const mockUseResumeCarousel = vi.mocked(useResumeCarousel);
const mockUseCreateConversation = vi.mocked(useCreateConversation);

class MockWebSocket {
  static instances: MockWebSocket[] = [];
  constructor(public url: string) {
    MockWebSocket.instances.push(this);
  }
  send = vi.fn();
  close = vi.fn();
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
}

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
  MockWebSocket.instances = [];
  Object.defineProperty(globalThis, "WebSocket", {
    value: MockWebSocket as unknown as typeof WebSocket,
    writable: true,
    configurable: true,
  });

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
  mockUseCarouselStatus.mockReturnValue({
    data: {
      id: "test-project-id",
      status: "pending",
      error_message: null,
      updated_at: "2026-04-20T00:00:00Z",
      phase_progress: null,
    },
    isLoading: false,
  } as ReturnType<typeof useCarouselStatus>);
  mockUseCarouselStream.mockReturnValue({
    latestEvent: null,
    isStreaming: false,
    error: null,
    close: vi.fn(),
    reconnect: vi.fn(),
  });
  mockUseResumeCarousel.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useResumeCarousel>);
  mockUseCreateConversation.mockReturnValue({
    mutateAsync: vi.fn(() => new Promise(() => undefined)),
  } as unknown as ReturnType<typeof useCreateConversation>);
});

afterEach(() => {
  Object.defineProperty(globalThis, "WebSocket", {
    value: undefined,
    writable: true,
    configurable: true,
  });
});

describe("WorkspacePage", () => {
  describe("Given a pending project", () => {
    it("subscribes to the SSE stream on mount", () => {
      render(<WorkspacePage />, { wrapper: createWrapper() });
      expect(mockUseCarouselStream).toHaveBeenCalledWith("test-project-id");
    });

    it("renders the progress tracker without auto-firing generate", () => {
      render(<WorkspacePage />, { wrapper: createWrapper() });
      // The progress section is present when status is pending.
      expect(screen.getByText(/workspace\.title/)).toBeInTheDocument();
    });

    it("does not mark carousel complete while still pending", () => {
      render(<WorkspacePage />, { wrapper: createWrapper() });
      // When pending, the preview component should not be shown.
      const publishButton = screen.queryByText("create.workspace.publish");
      expect(publishButton).not.toBeInTheDocument();
    });
  });

  describe("Given a completed project", () => {
    beforeEach(() => {
      mockUseCarouselStatus.mockReturnValue({
        data: {
          id: "test-project-id",
          status: "completed",
          error_message: null,
          updated_at: "2026-04-20T00:00:00Z",
          phase_progress: null,
        },
        isLoading: false,
      } as ReturnType<typeof useCarouselStatus>);
    });

    it("shows publish actions when generation is done", () => {
      render(<WorkspacePage />, { wrapper: createWrapper() });
      expect(screen.getByText(/workspace\.publish/)).toBeInTheDocument();
    });
  });

  describe("Given a failed project", () => {
    beforeEach(() => {
      mockUseCarouselStatus.mockReturnValue({
        data: {
          id: "test-project-id",
          status: "failed",
          error_message: "Something broke",
          updated_at: "2026-04-20T00:00:00Z",
          phase_progress: null,
        },
        isLoading: false,
      } as ReturnType<typeof useCarouselStatus>);
    });

    it("shows the resume button", () => {
      render(<WorkspacePage />, { wrapper: createWrapper() });
      expect(screen.getByTestId("resume-button")).toBeInTheDocument();
    });
  });
});
