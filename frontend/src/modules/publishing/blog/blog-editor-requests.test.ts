import { beforeEach, describe, expect, it, vi } from "vitest";
import { BLOG_EDITOR_ERROR_KINDS } from "@/constants/blog-editor";
import { blogPost, jsonResponse, SEC_2 } from "./editor.test-utils";

vi.mock("@/lib/authenticated-fetch", () => ({ authenticatedFetch: vi.fn() }));

import { authenticatedFetch } from "@/lib/authenticated-fetch";
import {
  approvePost,
  BlogEditorRequestError,
  cancelSchedule,
  errorKind,
  fetchEditorSettings,
  fetchVersions,
  fetchVoicePersonas,
  generateEnTranslation,
  generateSlotImage,
  patchSlotImage,
  publishPost,
  rejectPost,
  removeSlotImage,
  restoreVersion,
  rewriteSection,
  savePost,
  schedulePost,
  submitForReview,
  unpublishPost,
} from "./blog-editor-requests";

// Scenarios: tests/features/blog_editor_ae0424.feature

const mockFetch = vi.mocked(authenticatedFetch);
const LOCKED = { id: "p-1", lockVersion: 2 };

function lastCall(): { url: string; init: RequestInit } {
  const [url, init] = mockFetch.mock.calls[mockFetch.mock.calls.length - 1];
  return { url: String(url), init: init ?? {} };
}

function ifMatch(init: RequestInit): string | null {
  return new Headers(init.headers).get("If-Match");
}

beforeEach(() => {
  mockFetch.mockReset();
  mockFetch.mockImplementation(() => Promise.resolve(jsonResponse(blogPost())));
});

describe("errorKind", () => {
  // Scenario: A concurrent save conflict is surfaced
  it("maps a stale lock to version_conflict", () => {
    expect(errorKind(409, "version_conflict")).toBe(
      BLOG_EDITOR_ERROR_KINDS.VERSION_CONFLICT,
    );
    expect(errorKind(409, "blog_translation_exists")).toBe(
      BLOG_EDITOR_ERROR_KINDS.CONFLICT,
    );
  });

  // Scenario: A non-migrated row shows a blocking migration banner
  it("maps a non-v2 document 422 to migration_pending", () => {
    expect(errorKind(422, "blog_document_not_v2")).toBe(
      BLOG_EDITOR_ERROR_KINDS.MIGRATION_PENDING,
    );
    expect(errorKind(422, "invalid_blog_document: sections.0.id")).toBe(
      BLOG_EDITOR_ERROR_KINDS.MIGRATION_PENDING,
    );
    expect(errorKind(422, "blog_image_alt_blank")).toBe(
      BLOG_EDITOR_ERROR_KINDS.VALIDATION,
    );
    expect(errorKind(422, null)).toBe(BLOG_EDITOR_ERROR_KINDS.VALIDATION);
  });

  it("maps guard, not-found, AI and unknown failures", () => {
    expect(errorKind(400, "blog_invalid_status")).toBe(
      BLOG_EDITOR_ERROR_KINDS.STATUS_GUARD,
    );
    expect(errorKind(404, null)).toBe(BLOG_EDITOR_ERROR_KINDS.NOT_FOUND);
    expect(errorKind(502, null)).toBe(BLOG_EDITOR_ERROR_KINDS.AI_FAILED);
    expect(errorKind(500, null)).toBe(BLOG_EDITOR_ERROR_KINDS.FAILED);
  });
});

describe("content writes send If-Match", () => {
  it("saves with PUT and the lock version", async () => {
    await savePost(LOCKED, { title: "Novo" });
    const { url, init } = lastCall();
    expect(url).toBe("/api/blog-posts/p-1");
    expect(init.method).toBe("PUT");
    expect(ifMatch(init)).toBe("2");
    expect(JSON.parse(String(init.body))).toEqual({ title: "Novo" });
  });

  it("targets the cover and section image routes with the language", async () => {
    await generateSlotImage(LOCKED, {
      slot: { language: "pt", sectionId: null },
      prompt: null,
    });
    expect(lastCall().url).toBe("/api/blog-posts/p-1/cover/image?language=pt");
    expect(JSON.parse(String(lastCall().init.body))).toEqual({ prompt: null });
    await patchSlotImage(LOCKED, {
      slot: { language: "en", sectionId: SEC_2 },
      patch: { alt: "A" },
    });
    expect(lastCall().url).toBe(
      `/api/blog-posts/p-1/sections/${SEC_2}/image?language=en`,
    );
    expect(lastCall().init.method).toBe("PATCH");
    await removeSlotImage(LOCKED, { language: "pt", sectionId: SEC_2 });
    expect(lastCall().init.method).toBe("DELETE");
    expect(ifMatch(lastCall().init)).toBe("2");
  });

  it("rewrites, translates and restores with If-Match", async () => {
    await rewriteSection(LOCKED, {
      language: "pt",
      sectionId: SEC_2,
      personaId: "persona-1",
    });
    expect(lastCall().url).toBe(
      `/api/blog-posts/p-1/sections/${SEC_2}/rewrite?language=pt`,
    );
    expect(JSON.parse(String(lastCall().init.body))).toEqual({
      persona_id: "persona-1",
    });
    await generateEnTranslation(LOCKED);
    expect(lastCall().url).toBe("/api/blog-posts/p-1/translations/en");
    await restoreVersion(LOCKED, 3);
    expect(lastCall().url).toBe("/api/blog-posts/p-1/restore-version/3");
    expect(ifMatch(lastCall().init)).toBe("2");
  });

  it("throws a typed error with the API detail", async () => {
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ detail: "version_conflict" }, 409),
    );
    const error = await savePost(LOCKED, {}).catch((err: unknown) => err);
    expect(error).toBeInstanceOf(BlogEditorRequestError);
    expect(error).toMatchObject({
      kind: "version_conflict",
      detail: "version_conflict",
    });
  });

  it("keeps a null detail when the error body is not JSON", async () => {
    mockFetch.mockResolvedValueOnce(new Response("boom", { status: 500 }));
    await expect(savePost(LOCKED, {})).rejects.toMatchObject({
      kind: "failed",
      detail: null,
    });
  });
});

describe("workflow routes", () => {
  // Scenario: Submit for review moves the post to under review
  it("submits with or without an explicit reviewer", async () => {
    await submitForReview("p-1", "rev-1");
    expect(lastCall().url).toBe(
      "/api/blog-posts/p-1/submit-review?reviewer_id=rev-1",
    );
    await submitForReview("p-1", null);
    expect(lastCall().url).toBe("/api/blog-posts/p-1/submit-review");
  });

  it("approves, rejects with a reason, publishes and unpublishes", async () => {
    await approvePost("p-1");
    expect(lastCall().url).toBe("/api/blog-posts/p-1/approve");
    await rejectPost("p-1", "Falta fonte");
    expect(lastCall().url).toBe(
      "/api/blog-posts/p-1/reject?reason=Falta+fonte",
    );
    await publishPost(LOCKED);
    expect(lastCall().url).toBe("/api/blog-posts/p-1/publish");
    expect(ifMatch(lastCall().init)).toBe("2");
    await unpublishPost(LOCKED);
    expect(lastCall().url).toBe("/api/blog-posts/p-1/unpublish");
  });

  // Scenario: Scheduling publishes at the chosen time / Cancelling a schedule
  it("schedules and cancels", async () => {
    await schedulePost(LOCKED, "2026-10-20T10:00:00.000Z");
    expect(JSON.parse(String(lastCall().init.body))).toEqual({
      scheduled_publish_at: "2026-10-20T10:00:00.000Z",
    });
    await cancelSchedule(LOCKED);
    expect(lastCall().url).toBe("/api/blog-posts/p-1/schedule");
    expect(lastCall().init.method).toBe("DELETE");
  });

  it("reads the editor settings, versions and personas", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ allow_self_review: true }));
    expect(await fetchEditorSettings()).toEqual({ allow_self_review: true });
    mockFetch.mockResolvedValueOnce(jsonResponse([{ version_number: 1 }]));
    expect(await fetchVersions("p-1")).toEqual([{ version_number: 1 }]);
    expect(lastCall().url).toBe("/api/blog-posts/p-1/versions");
    mockFetch.mockResolvedValueOnce(
      jsonResponse({ items: [{ id: "x", name: "Pedro" }] }),
    );
    expect(await fetchVoicePersonas()).toEqual([{ id: "x", name: "Pedro" }]);
  });
});
