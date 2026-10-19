/**
 * Shared fixtures of the AE-0424 section editor tests.
 */

import type { BlogDocument, BlogImage } from "@/schemas/blog-document";
import type { BlogPost } from "./types";

export const SEC_1 = "sec_00000000-0000-4000-8000-000000000001";
export const SEC_2 = "sec_00000000-0000-4000-8000-000000000002";
export const SEC_3 = "sec_00000000-0000-4000-8000-000000000003";
export const EN_1 = "sec_00000000-0000-4000-8000-0000000000e1";

export function image(
  url = "https://cdn.example/a.jpg",
  alt = "Arte",
): BlogImage {
  return {
    url,
    alt,
    caption: null,
    source: "generated",
    prompt: "Um farol",
    model: "gpt-image-2",
  };
}

export function v2Document(withEnglish = false): BlogDocument {
  const document: BlogDocument = {
    schema: "blog.v2",
    cover: null,
    sections: [
      {
        id: SEC_1,
        heading: "Um",
        body_md: "Corpo um",
        image: image("https://cdn.example/1.jpg"),
      },
      {
        id: SEC_2,
        heading: "Dois",
        body_md: "Corpo dois",
        image: image("https://cdn.example/2.jpg"),
      },
      { id: SEC_3, heading: null, body_md: "Corpo três", image: null },
    ],
    translations: {},
    quality: null,
  };
  if (withEnglish) {
    document.translations = {
      en: {
        schema: "blog.v2",
        cover: null,
        sections: [
          { id: EN_1, heading: "One", body_md: "Body one", image: null },
        ],
        quality: null,
      },
    };
  }
  return document;
}

export function blogPost(overrides: Partial<BlogPost> = {}): BlogPost {
  return {
    id: "p-1",
    title: "GPT 5.6 saiu",
    slug: "gpt-5-6",
    status: "draft",
    content: v2Document(),
    excerpt: "",
    editor_comments: [],
    sources: [],
    citations: [],
    ai_suggestions: [],
    ai_generation_metadata: {},
    keywords: [],
    view_count: 0,
    like_count: 0,
    comment_count: 0,
    share_count: 0,
    created_at: "2026-10-18T00:00:00Z",
    updated_at: "2026-10-18T00:00:00Z",
    lock_version: 2,
    ...overrides,
  };
}

export function jsonResponse(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}
