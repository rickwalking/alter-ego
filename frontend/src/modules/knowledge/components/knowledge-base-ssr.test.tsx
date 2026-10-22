import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import type { ReactNode } from "react";
import { renderToString } from "react-dom/server";
import { beforeEach, describe, expect, it, vi } from "vitest";

import KnowledgePage from "@/app/dashboard/knowledge/page";

const apiCall = vi.hoisted(() => vi.fn());
vi.mock("@/lib/api-client", () => ({
  apiCall,
  apiCallNoContent: vi.fn(),
}));

function withQueryClient(children: ReactNode): React.ReactElement {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
}

describe("Knowledge page rendering", () => {
  beforeEach(() => {
    apiCall.mockReset();
    apiCall.mockResolvedValue({
      items: [
        {
          id: "doc-1",
          title: "Resume",
          content: "Body",
          metadata: { tags: [] },
          created_at: "2026-06-02T00:00:00Z",
          updated_at: "2026-06-02T00:00:00Z",
        },
      ],
    });
  });

  // Scenario: The server render shows the list skeleton without calling the API
  it("does not call the documents API during the server render", () => {
    const html = renderToString(withQueryClient(<KnowledgePage />));
    expect(apiCall).not.toHaveBeenCalled();
    expect(html).toContain("Knowledge Base");
  });

  // Scenario: The browser loads the documents after hydration
  it("loads the documents in the browser", async () => {
    render(withQueryClient(<KnowledgePage />));
    expect(await screen.findByText("Resume")).toBeInTheDocument();
    expect(apiCall).toHaveBeenCalledTimes(1);
  });

  // Scenario: The page has a single heading
  it("has exactly one level-1 heading", async () => {
    render(withQueryClient(<KnowledgePage />));
    await screen.findByText("Resume");
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
  });
});
