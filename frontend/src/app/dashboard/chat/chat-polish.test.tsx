/**
 * Gherkin: tests/features/chat-polish.feature
 */
import { describe, expect, it, vi } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";

import en from "@/i18n/locales/en.json";
import pt from "@/i18n/locales/pt.json";
import { COMPOSER_MAX_HEIGHT_PX, ChatComposer } from "./chat-composer";
import { CHAT_SUGGESTION_KEYS } from "./chat-empty-state";
import { ChatMessageList } from "./chat-message-list";

describe("chat polish", () => {
  /** Scenario: An empty chat introduces the Alter-Ego and suggests questions */
  it("introduces the Alter-Ego and sends a picked suggestion", () => {
    const onSuggestion = vi.fn();
    render(<ChatMessageList messages={[]} onSuggestion={onSuggestion} />);

    expect(
      screen.getByRole("heading", { name: en.chat.empty.title }),
    ).toBeInTheDocument();
    expect(screen.getByText(en.chat.empty.intro)).toBeInTheDocument();
    const suggestions = screen.getAllByRole("listitem");
    expect(suggestions).toHaveLength(4);

    fireEvent.click(screen.getByRole("button", { name: en.chat.empty.s3 }));
    expect(onSuggestion).toHaveBeenCalledWith(en.chat.empty.s3);
  });

  /** Scenario: An empty chat introduces the Alter-Ego and suggests questions */
  it("has every suggestion in Portuguese and hides them once the chat starts", () => {
    for (const key of CHAT_SUGGESTION_KEYS) {
      expect(pt.chat.empty[key]).toBeTruthy();
      expect(pt.chat.empty[key]).not.toBe(en.chat.empty[key]);
    }
    render(
      <ChatMessageList
        messages={[{ role: "user", text: "hi", time: "10:00" }]}
        onSuggestion={vi.fn()}
      />,
    );
    expect(screen.queryByText(en.chat.empty.title)).not.toBeInTheDocument();
  });

  /** Scenario: An empty chat introduces the Alter-Ego and suggests questions */
  it("shows no suggestions while an existing conversation loads", () => {
    render(<ChatMessageList messages={[]} />);
    expect(screen.queryByText(en.chat.empty.title)).not.toBeInTheDocument();
  });

  /** Scenario: The message box grows with multi-line text */
  it("grows the message box with its content up to the max height", () => {
    const { rerender } = render(
      <ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />,
    );
    const textarea = screen.getByRole("textbox");
    Object.defineProperty(textarea, "scrollHeight", {
      configurable: true,
      get: () => 96,
    });
    rerender(
      <ChatComposer value={"a\nb\nc\nd"} onChange={vi.fn()} onSend={vi.fn()} />,
    );
    expect(textarea.style.height).toBe("96px");
    expect(textarea.style.overflowY).toBe("hidden");

    Object.defineProperty(textarea, "scrollHeight", {
      configurable: true,
      get: () => 400,
    });
    rerender(
      <ChatComposer
        value={"long\n".repeat(20)}
        onChange={vi.fn()}
        onSend={vi.fn()}
      />,
    );
    expect(textarea.style.height).toBe("160px");
    expect(textarea.style.overflowY).toBe("auto");
  });

  /** Scenario: The message box grows with multi-line text */
  it("does not scroll at exactly the max height and shrinks back when emptied", () => {
    const { rerender } = render(
      <ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />,
    );
    const textarea = screen.getByRole("textbox");
    let height = COMPOSER_MAX_HEIGHT_PX;
    Object.defineProperty(textarea, "scrollHeight", {
      configurable: true,
      get: () => height,
    });
    rerender(
      <ChatComposer
        value={"a\n".repeat(6)}
        onChange={vi.fn()}
        onSend={vi.fn()}
      />,
    );
    expect(textarea.style.height).toBe("160px");
    expect(textarea.style.overflowY).toBe("hidden");

    height = 44;
    rerender(<ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />);
    expect(textarea.style.height).toBe("44px");
  });

  /** Scenario: The message box grows with multi-line text */
  it("adds the border to the measured text height", () => {
    const { rerender } = render(
      <ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />,
    );
    const textarea = screen.getByRole("textbox");
    Object.defineProperty(textarea, "scrollHeight", {
      configurable: true,
      get: () => 96,
    });
    Object.defineProperty(textarea, "offsetHeight", {
      configurable: true,
      get: () => 46,
    });
    Object.defineProperty(textarea, "clientHeight", {
      configurable: true,
      get: () => 44,
    });
    rerender(
      <ChatComposer value={"a\nb\nc\nd"} onChange={vi.fn()} onSend={vi.fn()} />,
    );
    expect(textarea.style.height).toBe("98px");
  });

  /** Scenario: The message box grows with multi-line text */
  it("measures the message box again when the window is resized", () => {
    render(<ChatComposer value="abc" onChange={vi.fn()} onSend={vi.fn()} />);
    const textarea = screen.getByRole("textbox");
    Object.defineProperty(textarea, "scrollHeight", {
      configurable: true,
      get: () => 120,
    });
    act(() => {
      window.innerWidth = 320;
      window.dispatchEvent(new Event("resize"));
    });
    expect(textarea.style.height).toBe("120px");
  });

  /** Scenario: A streaming reply can be stopped */
  it("shows Send, not Stop, once the reply is over", () => {
    render(
      <ChatComposer
        value="next"
        onChange={vi.fn()}
        onSend={vi.fn()}
        onStop={vi.fn()}
      />,
    );
    expect(
      screen.queryByRole("button", { name: "Stop the reply" }),
    ).not.toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: en.chat.input.send }),
    ).toBeEnabled();
  });

  /** Scenario: An empty chat introduces the Alter-Ego and suggests questions */
  it("shows no suggestions while the first reply is being written", () => {
    render(
      <ChatMessageList messages={[]} isStreaming onSuggestion={vi.fn()} />,
    );
    expect(screen.queryByText(en.chat.empty.title)).not.toBeInTheDocument();
  });

  /** Scenario: A streaming reply can be stopped */
  it("turns Send into Stop while a reply streams", () => {
    const onStop = vi.fn();
    render(
      <ChatComposer
        value=""
        onChange={vi.fn()}
        onSend={vi.fn()}
        busy
        onStop={onStop}
      />,
    );
    expect(
      screen.queryByRole("button", { name: en.chat.input.send }),
    ).not.toBeInTheDocument();
    const textarea = screen.getByRole("textbox");
    textarea.focus();
    const stop = screen.getByRole("button", { name: "Stop the reply" });
    fireEvent.pointerDown(stop);
    stop.focus();
    fireEvent.click(stop);
    expect(onStop).toHaveBeenCalledOnce();
    expect(textarea).toHaveFocus();
  });

  /** Scenario: A streaming reply can be stopped */
  it("leaves focus alone after Stop when the message box did not have it", () => {
    render(
      <ChatComposer
        value=""
        onChange={vi.fn()}
        onSend={vi.fn()}
        busy
        onStop={vi.fn()}
      />,
    );
    const stop = screen.getByRole("button", { name: "Stop the reply" });
    stop.focus();
    fireEvent.pointerDown(stop);
    fireEvent.click(stop);
    expect(screen.getByRole("textbox")).not.toHaveFocus();
  });

  /** Scenario: The typing label is plain language */
  it("says the Alter-Ego is typing", () => {
    render(<ChatMessageList messages={[]} isStreaming />);
    expect(screen.getAllByText("Alter-Ego is typing…").length).toBeGreaterThan(
      0,
    );
    expect(screen.queryByText(/tone alignment/i)).not.toBeInTheDocument();
  });
  /** Scenario: The conversation and the message box share one readable column */
  it("centres the thread and the message box in the same column", () => {
    render(
      <>
        <ChatMessageList
          messages={[{ role: "user", text: "hi", time: "10:00" }]}
        />
        <ChatComposer value="" onChange={vi.fn()} onSend={vi.fn()} />
      </>,
    );
    const thread = screen.getByText("hi").closest(".max-w-3xl");
    const box = screen.getByRole("textbox").closest(".max-w-3xl");
    expect(thread).toHaveClass("mx-auto", "w-full");
    expect(box).toHaveClass("mx-auto", "w-full");
    expect(screen.getByRole("log")).toContainElement(thread as HTMLElement);
  });
});
