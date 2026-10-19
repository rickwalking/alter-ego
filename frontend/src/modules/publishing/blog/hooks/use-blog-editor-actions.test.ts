import { act, renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { createElement, type ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  blogPost,
  image,
  jsonResponse,
  SEC_1,
  SEC_3,
  v2Document,
} from "../editor.test-utils";
import { updateSection, withServerTranslation } from "../lib/editor-document";
import {
  imageSlotKey,
  rewriteSlotKey,
  TRANSLATION_SLOT_KEY,
  useBlogEditorActions,
} from "./use-blog-editor-actions";
import { useBlogPostEditor } from "./use-blog-post-editor";

// Scenarios: tests/features/blog_editor_ae0424.feature (images, cover,
// rewrite in voice, PT/EN translation, migration banner)

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";

const mockFetch = vi.mocked(authenticatedFetch);
const SLOT = { language: "pt" as const, sectionId: SEC_3 };

function wrapper({ children }: { children: ReactNode }): ReactNode {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return createElement(QueryClientProvider, { client }, children);
}

async function renderActions() {
  mockFetch.mockResolvedValueOnce(jsonResponse(blogPost()));
  const hook = renderHook(
    () => {
      const editor = useBlogPostEditor("p-1");
      return { editor, actions: useBlogEditorActions(editor, "persona-1") };
    },
    { wrapper },
  );
  await waitFor(() => expect(hook.result.current.editor.draft).not.toBeNull());
  return hook;
}

function withSectionImage(): ReturnType<typeof v2Document> {
  return updateSection(v2Document(), "pt", {
    id: SEC_3,
    patch: { image: image("/api/blog-images/p-1/n.jpg") },
  });
}

beforeEach(() => {
  mockFetch.mockReset();
});

describe("image slots", () => {
  // Scenario: Generating a section image stores url, alt and prompt
  it("generates into the slot and keeps unsaved typing elsewhere", async () => {
    const { result } = await renderActions();
    mockFetch.mockResolvedValueOnce(
      jsonResponse(blogPost({ lock_version: 3, content: withSectionImage() })),
    );
    await act(async () => {
      await result.current.actions.generateImage(SLOT, "Um farol");
    });
    const [url, init] = mockFetch.mock.calls[1];
    expect(url).toBe(`/api/blog-posts/p-1/sections/${SEC_3}/image?language=pt`);
    expect(JSON.parse(String(init?.body))).toEqual({ prompt: "Um farol" });
    const draft = result.current.editor.draft?.document;
    expect(draft?.sections[2].image?.url).toBe("/api/blog-images/p-1/n.jpg");
    expect(result.current.editor.post?.lock_version).toBe(3);
    expect(result.current.actions.statusOf(imageSlotKey(SLOT))).toEqual({
      pending: false,
      error: null,
    });
  });

  it("saves pending edits before the action", async () => {
    const { result } = await renderActions();
    act(() =>
      result.current.editor.updateDraft((d) => ({ ...d, title: "Novo" })),
    );
    mockFetch.mockResolvedValueOnce(
      jsonResponse(blogPost({ title: "Novo", lock_version: 3 })),
    );
    mockFetch.mockResolvedValueOnce(
      jsonResponse(
        blogPost({
          title: "Novo",
          lock_version: 4,
          content: withSectionImage(),
        }),
      ),
    );
    await act(async () => {
      await result.current.actions.generateImage(SLOT, null);
    });
    expect(mockFetch.mock.calls[1][1]?.method).toBe("PUT");
    expect(
      new Headers(mockFetch.mock.calls[2][1]?.headers).get("If-Match"),
    ).toBe("3");
  });

  it("does not call the slot route when the save fails", async () => {
    const { result } = await renderActions();
    act(() =>
      result.current.editor.updateDraft((d) => ({ ...d, title: "Novo" })),
    );
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "version_conflict" }, 409),
    );
    await act(async () => {
      await result.current.actions.generateImage(SLOT, null);
    });
    expect(mockFetch).toHaveBeenCalledTimes(2);
    expect(result.current.actions.statusOf(imageSlotKey(SLOT)).pending).toBe(
      false,
    );
  });

  it("reports a running slot action (review controls wait for it)", async () => {
    const { result } = await renderActions();
    let finish: (value: Response) => void = () => undefined;
    mockFetch.mockReturnValueOnce(new Promise<Response>((r) => (finish = r)));
    let running: Promise<void> = Promise.resolve();
    act(() => {
      running = result.current.actions.generateImage(SLOT, null);
    });
    await waitFor(() => expect(result.current.actions.anyPending).toBe(true));
    await act(async () => {
      finish(
        jsonResponse(
          blogPost({ lock_version: 3, content: withSectionImage() }),
        ),
      );
      await running;
    });
    expect(result.current.actions.anyPending).toBe(false);
  });

  it("maps the image budget 429 to the budget error", async () => {
    const { result } = await renderActions();
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "blog_image_budget_exhausted" }, 429),
    );
    await act(async () => {
      await result.current.actions.generateImage(SLOT, null);
    });
    expect(
      result.current.actions.statusOf(imageSlotKey(SLOT)).error?.kind,
    ).toBe("budget");
  });

  // Scenario: A failed image generation shows a visible retry
  it("records the failure on that slot only", async () => {
    const { result } = await renderActions();
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "blog_image_generation_failed" }, 502),
    );
    await act(async () => {
      await result.current.actions.generateImage(SLOT, null);
    });
    expect(
      result.current.actions.statusOf(imageSlotKey(SLOT)).error?.kind,
    ).toBe("ai_failed");
    expect(
      result.current.actions.statusOf(
        imageSlotKey({ language: "pt", sectionId: null }),
      ).error,
    ).toBeNull();
    expect(result.current.editor.error).toBeNull();
  });

  // Scenario: A non-migrated row shows a blocking migration banner
  it("raises the migration banner on a non-v2 422", async () => {
    const { result } = await renderActions();
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "blog_document_not_v2" }, 422),
    );
    await act(async () => {
      await result.current.actions.generateImage(SLOT, null);
    });
    expect(result.current.editor.error).toEqual({
      kind: "migration_pending",
      detail: "blog_document_not_v2",
    });
  });

  it("maps a non-request error to failed", async () => {
    const { result } = await renderActions();
    mockFetch.mockRejectedValueOnce(new Error("offline"));
    await act(async () => {
      await result.current.actions.generateImage(SLOT, null);
    });
    expect(
      result.current.actions.statusOf(imageSlotKey(SLOT)).error?.kind,
    ).toBe("failed");
  });
});

describe("rewrite and translation", () => {
  // Scenario: Rewrite this section in my voice replaces only that section
  it("rewrites one section with the chosen persona", async () => {
    const { result } = await renderActions();
    const server = updateSection(v2Document(), "pt", {
      id: SEC_1,
      patch: { body_md: "Na minha voz" },
    });
    mockFetch.mockResolvedValueOnce(
      jsonResponse(blogPost({ lock_version: 3, content: server })),
    );
    await act(async () => {
      await result.current.actions.rewrite(SEC_1);
    });
    expect(JSON.parse(String(mockFetch.mock.calls[1][1]?.body))).toEqual({
      persona_id: "persona-1",
    });
    const sections = result.current.editor.draft?.document.sections ?? [];
    expect(sections.map((s) => s.body_md)).toEqual([
      "Na minha voz",
      "Corpo dois",
      "Corpo três",
    ]);
    expect(
      result.current.actions.statusOf(
        rewriteSlotKey({ language: "pt", sectionId: SEC_1 }),
      ).pending,
    ).toBe(false);
  });

  // Scenario: A missing EN translation is read-only with a generate action
  it("generates the EN translation and makes it editable", async () => {
    const { result } = await renderActions();
    const server = withServerTranslation(v2Document(), v2Document(true));
    mockFetch.mockResolvedValueOnce(
      jsonResponse(blogPost({ lock_version: 3, content: server })),
    );
    await act(async () => {
      await result.current.actions.generateTranslation();
    });
    expect(mockFetch.mock.calls[1][0]).toBe(
      "/api/blog-posts/p-1/translations/en",
    );
    expect(
      result.current.editor.draft?.document.translations.en.sections,
    ).toHaveLength(1);
    expect(
      result.current.actions.statusOf(TRANSLATION_SLOT_KEY).error,
    ).toBeNull();
  });
});
