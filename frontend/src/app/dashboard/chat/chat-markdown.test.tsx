/**
 * Gherkin: tests/features/chat-markdown.feature
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { ChatMarkdown } from "./chat-markdown";
import { ChatMessageList } from "./chat-message-list";

function renderMarkdown(text: string) {
  return render(<ChatMarkdown text={text} />).container;
}

describe("ChatMarkdown", () => {
  /** Scenario: Assistant replies render markdown formatting */
  it("renders bold, headings and lists instead of raw markers", () => {
    const container = renderMarkdown(
      "## Topics\n\n**Bold** words\n\n- one\n- two",
    );
    expect(container.textContent).not.toMatch(/\*\*|##/);
    expect(screen.getByText("Bold").tagName).toBe("STRONG");
    expect(screen.getAllByRole("listitem")).toHaveLength(2);
    expect(screen.getByText("Topics")).toBeInTheDocument();
  });

  /** Scenario: Code blocks keep their text in a preformatted block */
  it("renders a fenced code block as pre/code without the fences", () => {
    const container = renderMarkdown('```python\nprint("hi")\n```');
    const pre = container.querySelector("pre");
    expect(pre?.textContent).toBe('print("hi")\n');
    expect(container.textContent).not.toContain("```");
  });

  /** Scenario: Links are clickable and safe */
  it("makes http links clickable in a new tab with noopener nofollow", () => {
    renderMarkdown("See [Python's site](https://python.org).");
    const link = screen.getByRole("link", { name: "Python's site" });
    expect(link).toHaveAttribute("href", "https://python.org");
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer nofollow");
  });

  /** Scenario: Links are clickable and safe */
  it("never makes a javascript: link clickable", () => {
    renderMarkdown("[click me](javascript:alert(1))");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
    expect(screen.getByText("click me")).toBeInTheDocument();
  });

  /** Scenario: Links are clickable and safe */
  it("does not make a protocol-relative link clickable", () => {
    renderMarkdown("[away](//evil.test)");
    expect(screen.queryByRole("link")).not.toBeInTheDocument();
  });

  /** Scenario: Raw HTML and images are never rendered */
  it("keeps a link whose only content was an image readable", () => {
    renderMarkdown("[![logo](https://cdn.test/l.png)](https://python.org)");
    expect(
      screen.getByRole("link", { name: "https://python.org" }),
    ).toBeInTheDocument();
  });

  /** Scenario: Code blocks keep their text in a preformatted block */
  it("lets a long reply shrink to the screen so code scrolls inside its block", () => {
    const { container } = render(
      <ChatMessageList
        messages={[{ role: "assistant", text: "```\nx\n```", time: "10:00" }]}
      />,
    );
    const pre = container.querySelector("pre")!;
    const row = pre.closest<HTMLElement>('[style*="max-width"]')!;
    const column = pre.closest<HTMLElement>('[style*="min-width"]')!;
    expect(row.style.maxWidth).toBe("min(720px, 100%)");
    expect(column.style.minWidth).toBe("0");
    expect(pre.style.overflowX).toBe("auto");
  });

  /** Scenario: Raw HTML and images are never rendered */
  it("drops raw HTML and images", () => {
    const container = renderMarkdown(
      'Hi <img src=x onerror="alert(1)"><script>alert(1)</script>\n\n![tracker](https://evil.test/p.png)',
    );
    expect(container.querySelector("img, script")).toBeNull();
    expect(container.innerHTML).not.toContain("onerror");
  });
});

describe("ChatMessageList markdown", () => {
  /** Scenario: Visitor messages stay plain text */
  it("renders the assistant's markdown but shows the visitor's text as typed", () => {
    render(
      <ChatMessageList
        messages={[
          { role: "user", text: "**not bold**", time: "10:00" },
          { role: "assistant", text: "**bold**", time: "10:00" },
        ]}
      />,
    );
    expect(screen.getByText("**not bold**")).toBeInTheDocument();
    expect(screen.getByText("bold").tagName).toBe("STRONG");
  });
});
