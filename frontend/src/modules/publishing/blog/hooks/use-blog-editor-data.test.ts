import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { jsonResponse } from "../editor.test-utils";
import { useBlogEditorData } from "./use-blog-editor-data";

/**
 * (tests/features/blog_editor_ae0424.feature)
 */
// Scenario: Saving appends a version snapshot visible in the sidebar

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);

function wrapper({ children }: { children: ReactNode }): ReactNode {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client }, children);
}

beforeEach(() => {
  mockFetch.mockReset();
  mockFetch.mockImplementation((url) =>
    Promise.resolve(
      url.endsWith("/versions")
        ? jsonResponse([{ version_number: 1, snapshot: {} }])
        : jsonResponse({
            items: [
              { id: "a", name: "Pedro" },
              { id: "b", name: "Outra" },
            ],
          }),
    ),
  );
});

describe("useBlogEditorData", () => {
  it("re-reads versions when the lock version changes and defaults the persona", async () => {
    const { result, rerender } = renderHook(
      ({ lock }) => useBlogEditorData("p-1", lock),
      {
        wrapper,
        initialProps: { lock: 2 },
      },
    );
    await waitFor(() => expect(result.current.versions).toHaveLength(1));
    await waitFor(() => expect(result.current.personaId).toBe("a"));
    rerender({ lock: 3 });
    await waitFor(() =>
      expect(
        mockFetch.mock.calls.filter(([url]) => url.endsWith("/versions")),
      ).toHaveLength(2),
    );
    act(() => result.current.setPersonaId("b"));
    expect(result.current.personaId).toBe("b");
  });

  it("has no persona when none exist", async () => {
    mockFetch.mockImplementation(() =>
      Promise.resolve(jsonResponse({ items: [] })),
    );
    const { result } = renderHook(() => useBlogEditorData("", 0), { wrapper });
    await waitFor(() => expect(result.current.personas).toEqual([]));
    expect(result.current.personaId).toBeNull();
    expect(result.current.versions).toEqual([]);
  });
});
