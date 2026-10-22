import { describe, expect, it, vi } from "vitest";

const guard = vi.hoisted(() => vi.fn(() => Promise.resolve()));
vi.mock("@/lib/owner-resource", () => ({ notFoundUnlessOwnerResource: guard }));

import CreateProjectLayout from "./layout";
import BlogPostLayout from "@/app/dashboard/blog-posts/[id]/layout";

const ID = "0f8fad5b-d9cb-469f-a165-70867728950e";

describe("dashboard id layouts", () => {
  // Scenario: An unknown carousel workspace answers 404
  it("checks the carousel before rendering the workspace", async () => {
    const child = <p>workspace</p>;
    const result = await CreateProjectLayout({
      children: child,
      params: Promise.resolve({ id: ID }),
    });
    expect(result).toBe(child);
    const [id, path] = guard.mock.calls[0] as unknown as [
      string,
      (id: string) => string,
    ];
    expect(id).toBe(ID);
    expect(path(ID)).toBe(`/api/carousels/${ID}`);
  });

  // Scenario: An unknown blog post editor answers 404
  it("checks the blog post before rendering the editor", async () => {
    const child = <p>editor</p>;
    const result = await BlogPostLayout({
      children: child,
      params: Promise.resolve({ id: ID }),
    });
    expect(result).toBe(child);
    const [, path] = guard.mock.calls.at(-1) as unknown as [
      string,
      (id: string) => string,
    ];
    expect(path(ID)).toBe(`/api/blog-posts/${ID}`);
  });
});
