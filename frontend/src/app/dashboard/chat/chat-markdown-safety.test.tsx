/**
 * Gherkin: tests/features/chat-markdown.feature
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ChatMarkdown } from "./chat-markdown";
import { ChatMarkdownBoundary } from "./chat-markdown-boundary";
import {
  CHAT_MARKDOWN_MAX_LENGTH,
  CHAT_MARKDOWN_MAX_NESTING,
  isRenderableMarkdown,
} from "./chat-markdown-guard";

function renderMarkdown(text: string) {
  return render(<ChatMarkdown text={text} />).container;
}

describe("ChatMarkdown hostile input", () => {
  /** Scenario: A reply the renderer cannot take shows as plain text */
  it.each([
    ["a 900-level list", `${"- ".repeat(900)}a`],
    ["a 3000-level quote", ">".repeat(3000)],
  ])("shows %s as plain text instead of crashing", (_name, text) => {
    const container = renderMarkdown(text);
    expect(container.textContent).toBe(text);
    expect(container.querySelector("ul, blockquote")).toBeNull();
  });

  /** Scenario: A reply the renderer cannot take shows as plain text */
  it("renders up to the nesting limit and falls back one level past it", () => {
    const atLimit = `${"- ".repeat(CHAT_MARKDOWN_MAX_NESTING)}a`;
    const pastLimit = `${"> ".repeat(CHAT_MARKDOWN_MAX_NESTING + 1)}a`;
    const indented = Array.from(
      { length: CHAT_MARKDOWN_MAX_NESTING + 2 },
      (_, depth) => `${"  ".repeat(depth)}- item`,
    ).join("\n");

    expect(isRenderableMarkdown(atLimit)).toBe(true);
    expect(isRenderableMarkdown(pastLimit)).toBe(false);
    expect(isRenderableMarkdown(indented)).toBe(false);
    expect(isRenderableMarkdown("1. a\n2. b\n> quote")).toBe(true);
  });

  /** Scenario: A reply the renderer cannot take shows as plain text */
  it("shows an over-long reply as plain text", () => {
    const text = `**${"x".repeat(CHAT_MARKDOWN_MAX_LENGTH)}**`;
    expect(isRenderableMarkdown("x".repeat(CHAT_MARKDOWN_MAX_LENGTH))).toBe(
      true,
    );
    const container = renderMarkdown(text);
    expect(container.querySelector("strong")).toBeNull();
    expect(container.textContent).toBe(text);
  });

  /** Scenario: A reply the renderer cannot take shows as plain text */
  it("shows the fallback when rendering still throws", () => {
    function Explodes(): React.ReactElement {
      throw new RangeError("Maximum call stack size exceeded");
    }
    render(
      <ChatMarkdownBoundary fallback={<p>plain reply</p>}>
        <Explodes />
      </ChatMarkdownBoundary>,
    );
    expect(screen.getByText("plain reply")).toBeInTheDocument();
  });

  /** Scenario: Unsafe or empty links stay readable text */
  it.each([
    ["mixed-case data:", "[x](DaTa:text/html,<script>alert(1)</script>)"],
    ["mixed-case vbscript:", "[x](VbScRiPt:msgbox(1))"],
    ["entity-encoded javascript:", "[x](&#x6A;avascript:alert(1))"],
    ["an autolink", "<javascript:alert(1)>"],
    ["a reference-style link", "[x][r]\n\n[r]: javascript:alert(1)"],
  ])("never makes %s clickable", (_name, text) => {
    renderMarkdown(text);
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });
});

describe("ChatMarkdown link targets", () => {
  /** Scenario: Unsafe or empty links stay readable text */
  it("keeps a tab-split protocol-relative link on this site", () => {
    renderMarkdown("[x](</\t/evil.test>)");
    const href = screen.getByRole("link", { name: "x" }).getAttribute("href");
    expect(href).toBe("/%09/evil.test");
    expect(new URL(href ?? "", "https://marinssolutions.com").host).toBe(
      "marinssolutions.com",
    );
  });

  /** Scenario: Links are clickable and safe */
  it("keeps same-site links and anchors in the same tab", () => {
    renderMarkdown("[post](/blog/post) and [top](#top)");
    for (const name of ["post", "top"]) {
      const link = screen.getByRole("link", { name });
      expect(link).not.toHaveAttribute("target");
      expect(link).not.toHaveAttribute("rel");
    }
  });

  /** Scenario: Links are clickable and safe */
  it("shows the host next to an external link", () => {
    const container = renderMarkdown("Read the [docs](https://evil.test/a?b).");
    expect(screen.getByRole("link", { name: "docs" })).toHaveAttribute(
      "target",
      "_blank",
    );
    expect(container.textContent).toBe("Read the docs (evil.test).");
  });

  /** Scenario: Links are clickable and safe */
  it("does not repeat the host when the link text is the address", () => {
    const container = renderMarkdown("<https://python.org>");
    expect(container.textContent).toBe("https://python.org");
  });
});
