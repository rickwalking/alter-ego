import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("next/headers", () => ({
  cookies: () => Promise.resolve({ toString: () => "access_token=jwt" }),
}));
vi.mock("next/navigation", () => ({
  notFound: () => {
    throw new Error("NEXT_NOT_FOUND");
  },
}));

import CreateProjectLayout from "./layout";
import BlogPostLayout from "@/app/dashboard/blog-posts/[id]/layout";

const ID = "0f8fad5b-d9cb-469f-a165-70867728950e";
const fetchMock = vi.fn();

beforeEach(() => {
  fetchMock.mockReset();
  vi.stubGlobal("fetch", fetchMock);
});

function props(id: string) {
  return { children: <p>page</p>, params: Promise.resolve({ id }) };
}

describe("dashboard id layouts", () => {
  // Scenario: An unknown carousel workspace answers 404
  it("checks the carousel before rendering the workspace", async () => {
    fetchMock.mockResolvedValue({ ok: true, status: 200 });
    const page = props(ID);
    expect(await CreateProjectLayout(page)).toBe(page.children);
    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(
      new RegExp(`/api/carousels/${ID}$`),
    );
  });

  // Scenario: An unknown blog post editor answers 404
  it("answers not-found for a blog post the backend does not have", async () => {
    fetchMock.mockResolvedValue({ ok: false, status: 404 });
    await expect(BlogPostLayout(props(ID))).rejects.toThrow("NEXT_NOT_FOUND");
    expect(String(fetchMock.mock.calls[0]?.[0])).toMatch(
      new RegExp(`/api/blog-posts/${ID}$`),
    );
  });

  // Scenario: A malformed id answers 404 without asking the backend
  it("answers not-found for a malformed id without a backend call", async () => {
    await expect(CreateProjectLayout(props("not-a-uuid"))).rejects.toThrow(
      "NEXT_NOT_FOUND",
    );
    expect(fetchMock).not.toHaveBeenCalled();
  });
});
