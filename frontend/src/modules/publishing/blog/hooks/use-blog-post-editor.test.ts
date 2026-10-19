import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  blogPost,
  jsonResponse,
  SEC_1,
  v2Document,
} from "../editor.test-utils";
import { updateSection } from "../lib/editor-document";
import { useBlogPostEditor } from "./use-blog-post-editor";

// Scenarios: tests/features/blog_editor_ae0424.feature (section editing,
// versions, concurrent save conflict, migration banner) and
// tests/features/blog-dashboard-ae0411.feature (Editor load/save)

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);

function wrapper({ children }: { children: ReactNode }): ReactNode {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client }, children);
}

async function renderLoaded(post = blogPost()) {
  mockFetch.mockResolvedValueOnce(jsonResponse(post));
  const hook = renderHook(() => useBlogPostEditor("p-1"), { wrapper });
  await waitFor(() => expect(hook.result.current.draft).not.toBeNull());
  return hook;
}

function lastBody(): Record<string, unknown> {
  const [, init] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
  return JSON.parse(String(init?.body)) as Record<string, unknown>;
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("useBlogPostEditor load", () => {
  it("loads the detail endpoint into a v2 draft", async () => {
    const { result } = await renderLoaded();
    expect(mockFetch.mock.calls[0][0]).toBe("/api/blog-posts/p-1");
    expect(result.current.draft?.document.sections).toHaveLength(3);
    expect(result.current.language).toBe("pt");
    expect(result.current.dirty).toBe(false);
  });

  // Scenario: A non-migrated row shows a blocking migration banner
  it("never parses a legacy body: the draft is null (migration pending)", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse(blogPost({ content: { markdown: "# x" } })),
    );
    const { result } = renderHook(() => useBlogPostEditor("p-1"), { wrapper });
    await waitFor(() => expect(result.current.post).toBeDefined());
    expect(result.current.draft).toBeNull();
    expect(await result.current.handleSave()).toBe(true);
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  it("reports a failed load", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({}, 500));
    const { result } = renderHook(() => useBlogPostEditor("p-1"), { wrapper });
    await waitFor(() => expect(result.current.loadFailed).toBe(true));
  });
});

describe("useBlogPostEditor save", () => {
  // Scenario: Editing a section heading and body persists it
  it("PUTs the merged document with If-Match and takes the saved post", async () => {
    const { result } = await renderLoaded();
    act(() =>
      result.current.updateDraft((d) => ({
        ...d,
        document: updateSection(d.document, "pt", {
          id: SEC_1,
          patch: { body_md: "Novo" },
        }),
      })),
    );
    expect(result.current.dirty).toBe(true);
    const saved = blogPost({
      lock_version: 3,
      content: result.current.draft?.document,
    });
    mockFetch.mockResolvedValueOnce(jsonResponse(saved));
    let ok = false;
    await act(async () => {
      ok = await result.current.handleSave();
    });
    expect(ok).toBe(true);
    const [, init] = mockFetch.mock.calls[1];
    expect(new Headers(init?.headers).get("If-Match")).toBe("2");
    const content = lastBody().content as ReturnType<typeof v2Document>;
    expect(content.sections[0].body_md).toBe("Novo");
    expect(content.sections[1]).toEqual(v2Document().sections[1]);
    expect(result.current.post?.lock_version).toBe(3);
    expect(result.current.dirty).toBe(false);
  });

  it("does not call the API when nothing changed or the draft is invalid", async () => {
    const { result } = await renderLoaded();
    await act(async () => {
      expect(await result.current.handleSave()).toBe(true);
    });
    act(() => result.current.updateDraft((d) => ({ ...d, title: " " })));
    await act(async () => {
      expect(await result.current.handleSave()).toBe(false);
    });
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  // Scenario: A concurrent save conflict is surfaced
  it("keeps the unsaved draft on a 409 conflict", async () => {
    const { result } = await renderLoaded();
    act(() =>
      result.current.updateDraft((d) => ({ ...d, title: "Meu texto" })),
    );
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "version_conflict" }, 409),
    );
    await act(async () => {
      expect(await result.current.handleSave()).toBe(false);
    });
    expect(result.current.error).toEqual({
      kind: "version_conflict",
      detail: "version_conflict",
    });
    expect(result.current.draft?.title).toBe("Meu texto");
    expect(result.current.dirty).toBe(true);
  });

  it("ensureSaved returns the locked post after saving pending edits", async () => {
    const { result } = await renderLoaded();
    await act(async () => {
      expect(await result.current.ensureSaved()).toEqual({
        id: "p-1",
        lockVersion: 2,
      });
    });
    act(() => result.current.updateDraft((d) => ({ ...d, title: "Novo" })));
    mockFetch.mockResolvedValueOnce(
      jsonResponse(blogPost({ title: "Novo", lock_version: 5 })),
    );
    await act(async () => {
      expect(await result.current.ensureSaved()).toEqual({
        id: "p-1",
        lockVersion: 5,
      });
    });
    mockFetch.mockRejectedValueOnce(new Error("offline"));
    act(() => result.current.updateDraft((d) => ({ ...d, title: "Outro" })));
    await act(async () => {
      expect(await result.current.ensureSaved()).toBeNull();
    });
    expect(result.current.error?.kind).toBe("failed");
  });
});

describe("useBlogPostEditor server answers", () => {
  it("applyServerPost keeps other edits and merges the slot", async () => {
    const { result } = await renderLoaded();
    act(() =>
      result.current.updateDraft((d) => ({ ...d, title: "Digitando" })),
    );
    const server = blogPost({ lock_version: 3 });
    act(() => result.current.applyServerPost(server, (draftDoc) => draftDoc));
    expect(result.current.post?.lock_version).toBe(3);
    expect(result.current.draft?.title).toBe("Digitando");
  });

  // Scenario: Restoring a version loads it into the editor
  it("restores a version through the API and loads it", async () => {
    const { result } = await renderLoaded();
    const restored = blogPost({ title: "Versão 1", lock_version: 4 });
    mockFetch.mockResolvedValueOnce(jsonResponse(restored));
    await act(async () => {
      expect(await result.current.handleRestore(1)).toBe(true);
    });
    expect(mockFetch.mock.calls[1][0]).toBe(
      "/api/blog-posts/p-1/restore-version/1",
    );
    expect(result.current.draft?.title).toBe("Versão 1");
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "version_conflict" }, 409),
    );
    await act(async () => {
      expect(await result.current.handleRestore(1)).toBe(false);
    });
    expect(result.current.error?.kind).toBe("version_conflict");
  });

  it("reload re-reads the post", async () => {
    const { result } = await renderLoaded();
    mockFetch.mockResolvedValueOnce(
      jsonResponse(blogPost({ status: "under_review" })),
    );
    await act(async () => {
      await result.current.reload();
    });
    expect(result.current.post?.status).toBe("under_review");
  });
});
