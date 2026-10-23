import { describe, expect, it } from "vitest";
import {
  isSafeMarkdownHref,
  normalizeMarkdownHref,
} from "./safe-markdown-href";

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

  /** Scenario: Links are clickable and safe */
  it("rejects protocol-relative links that leave the site", () => {
    expect(isSafeMarkdownHref("//evil.test/path")).toBe(false);
    expect(isSafeMarkdownHref("/\\evil.test")).toBe(false);
    expect(isSafeMarkdownHref("/blog/post")).toBe(true);
  });

  /** Scenario: Unsafe or empty links stay readable text */
  it("reads the href as a browser does before deciding", () => {
    expect(normalizeMarkdownHref("/\t/evil.test")).toBe("//evil.test");
    expect(normalizeMarkdownHref("\u0001 https://a.test/\n ")).toBe(
      "https://a.test/",
    );
    expect(isSafeMarkdownHref("/\t/evil.test")).toBe(false);
    expect(isSafeMarkdownHref("/\n\\evil.test")).toBe(false);
    expect(isSafeMarkdownHref("/blog/\tpost")).toBe(true);
  });
});
