import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import PublishPage from "./page";

vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "project-1" }),
}));

vi.mock("next-intl", () => ({
  useTranslations: () => (key: string) => key,
}));

vi.mock("@/components/layout", () => ({
  Header: () => <div>Header</div>,
}));

vi.mock("@/features/chat/components", () => ({
  MessageInput: () => <div>MessageInput</div>,
  MessageList: () => <div>MessageList</div>,
}));

vi.mock("@/features/publish/components", () => ({
  PublishPanel: () => <div>PublishPanel</div>,
}));

vi.mock("@/features/publish/hooks", () => ({
  usePublishInstagram: () => ({
    mutateAsync: vi.fn(),
    isPending: false,
  }),
  usePublishChat: () => ({
    messages: [],
    isStreaming: false,
    sendMessage: vi.fn(),
  }),
}));

const mockRefreshState = vi.fn().mockResolvedValue(undefined);

vi.mock("@/features/create/hooks", () => ({
  useCarouselProject: () => ({
    data: {
      id: "project-1",
      topic: "Topic",
      audience: "Audience",
      niche: "AI",
      title: "Title",
    },
    isLoading: false,
  }),
}));

vi.mock("@/features/create/hooks/use-editorial-workflow", () => ({
  useEditorialWorkflow: () => ({
    state: { workflow_status: "approved_for_publish" },
    refreshState: mockRefreshState,
  }),
}));

describe("PublishPage", () => {
  beforeEach(() => {
    mockRefreshState.mockClear();
  });

  // Scenario: Publish panel appears after final review approval
  it("shows publish to site action when workflow is approved for publish", () => {
    render(<PublishPage />);
    expect(screen.getByRole("button", { name: "publishToSite" })).toBeInTheDocument();
    expect(screen.getByText("PublishPanel")).toBeInTheDocument();
  });
});
