/**
 * Gherkin: tests/features/chat-markdown.feature
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

const renders = vi.hoisted(() => ({ texts: [] as string[], fail: false }));

vi.mock("react-markdown", async (importOriginal) => {
  const real = await importOriginal<typeof import("react-markdown")>();
  return {
    default: (props: Parameters<typeof real.default>[0]) => {
      renders.texts.push(String(props.children));
      if (renders.fail)
        throw new RangeError("Maximum call stack size exceeded");
      return real.default(props);
    },
  };
});

import { ChatMarkdown } from "./chat-markdown";
import { ChatMessageList } from "./chat-message-list";

describe("ChatMarkdown rendering cost", () => {
  /** Scenario: A streamed token re-renders only the reply it extends */
  it("does not re-parse earlier replies while a new one streams", () => {
    renders.texts = [];
    renders.fail = false;
    const earlier = { role: "assistant" as const, text: "**old**", time: "1" };
    const question = { role: "user" as const, text: "next?", time: "2" };
    const { rerender } = render(
      <ChatMessageList
        messages={[
          earlier,
          question,
          { role: "assistant", text: "Ne", time: "3" },
        ]}
        isStreaming
      />,
    );
    rerender(
      <ChatMessageList
        messages={[
          { ...earlier },
          { ...question },
          { role: "assistant", text: "New reply", time: "3" },
        ]}
        isStreaming
      />,
    );
    expect(renders.texts.filter((text) => text === "**old**")).toHaveLength(1);
    expect(renders.texts).toContain("New reply");
  });

  /** Scenario: A reply the renderer cannot take shows as plain text */
  it("falls back to the plain reply when the renderer throws", () => {
    renders.fail = true;
    vi.spyOn(console, "error").mockImplementation(() => undefined);
    render(<ChatMarkdown text="**boom**" />);
    expect(screen.getByText("**boom**")).toBeInTheDocument();
    renders.fail = false;
  });
});
