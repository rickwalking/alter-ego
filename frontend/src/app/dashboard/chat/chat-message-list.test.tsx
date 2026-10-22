/**
 * Gherkin: tests/features/chat-stream-state.feature (auto-scroll scenarios).
 */
import { describe, expect, it } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import type { DashboardChatMessage } from "@/modules/editorial-operations";
import { ChatMessageList } from "./chat-message-list";

const VIEWPORT_PX = 400;

function message(
  role: DashboardChatMessage["role"],
  text: string,
): DashboardChatMessage {
  return { role, text, time: "10:00" };
}

/** jsdom has no layout: give the list a fixed viewport and a content height. */
function fakeLayout(element: HTMLElement, contentHeight: () => number): void {
  Object.defineProperty(element, "clientHeight", {
    configurable: true,
    get: () => VIEWPORT_PX,
  });
  Object.defineProperty(element, "scrollHeight", {
    configurable: true,
    get: contentHeight,
  });
}

function renderList(messages: DashboardChatMessage[], isStreaming = false) {
  const view = render(
    <ChatMessageList messages={messages} isStreaming={isStreaming} />,
  );
  const list = screen.getByTestId("chat-message-list");
  let height = 1000;
  fakeLayout(list, () => height);
  return {
    list,
    grow: (next: DashboardChatMessage[], streaming = isStreaming) => {
      height += 200;
      view.rerender(
        <ChatMessageList messages={next} isStreaming={streaming} />,
      );
    },
  };
}

describe("ChatMessageList auto-scroll", () => {
  const question = message("user", "question");

  // Scenario: New replies scroll into view
  it("scrolls to the bottom as streamed text arrives", () => {
    const { list, grow } = renderList([question], true);

    grow([question, message("assistant", "Hel")]);
    grow([question, message("assistant", "Hello there")]);

    expect(list.scrollTop).toBe(1400);
  });

  // Scenario: A reader who scrolled up is not pulled down
  it("leaves the position alone when the reader scrolled up", () => {
    const { list, grow } = renderList([question], true);
    grow([question, message("assistant", "Hel")]);

    list.scrollTop = 100;
    fireEvent.scroll(list);
    grow([question, message("assistant", "Hello there")]);

    expect(list.scrollTop).toBe(100);
  });

  // Scenario: New replies scroll into view
  it("scrolls down again when the reader sends a new message", () => {
    const answer = message("assistant", "answer");
    const { list, grow } = renderList([question, answer]);
    list.scrollTop = 0;
    fireEvent.scroll(list);

    grow([question, answer, message("user", "follow-up")], true);

    expect(list.scrollTop).toBe(1200);
  });

  // Scenario: New replies scroll into view
  it("scrolls down when the reader retries a failed message", () => {
    const { list, grow } = renderList([question]);
    list.scrollTop = 0;
    fireEvent.scroll(list);

    grow([question], true);

    expect(list.scrollTop).toBe(1200);
  });
});
