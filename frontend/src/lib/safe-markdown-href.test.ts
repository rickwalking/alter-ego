import { describe, expect, it } from "vitest";
import { isSafeMarkdownHref } from "./safe-markdown-href";

describe("isSafeMarkdownHref", () => {
  it("allows http and https links", () => {
    expect(isSafeMarkdownHref("https://example.com/path")).toBe(true);
    expect(isSafeMarkdownHref("http://example.com")).toBe(true);
  });

  it("allows mailto and relative paths", () => {
    expect(isSafeMarkdownHref("mailto:user@example.com")).toBe(true);
    expect(isSafeMarkdownHref("/blog/post-id")).toBe(true);
    expect(isSafeMarkdownHref("#section")).toBe(true);
  });

  it("blocks javascript and data URLs", () => {
    expect(isSafeMarkdownHref("javascript:alert(1)")).toBe(false);
    expect(isSafeMarkdownHref("data:text/html,<script>")).toBe(false);
  });

  it("rejects empty or missing href", () => {
    expect(isSafeMarkdownHref("")).toBe(false);
    expect(isSafeMarkdownHref(undefined)).toBe(false);
  });
});
