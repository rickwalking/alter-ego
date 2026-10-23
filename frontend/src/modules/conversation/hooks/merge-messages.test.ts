/**
 * Gherkin: tests/features/chat-polish.feature
 */
import { describe, expect, it } from "vitest";

import type { Message } from "@/schemas/chat";
import { mergeMessages } from "./merge-messages";

function message(role: Message["role"], content: string): Message {
  return {
    id: `${role}-${content}`,
    role,
    content,
    sources: [],
    created_at: "t",
  };
}

const STOPPED = { stopped: true, turnStart: 0 };
const STREAMING = { stopped: false, turnStart: 0 };

const contents = (messages: Message[]): string[] =>
  messages.map((m) => m.content);

describe("mergeMessages", () => {
  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("drops the stopped part once this question's reply is saved", () => {
    const history = [
      message("user", "story"),
      message("assistant", "Once upon a time."),
    ];
    const optimistic = [
      message("user", "story"),
      message("assistant", "Once upon"),
    ];

    expect(contents(mergeMessages(history, optimistic, STOPPED))).toEqual([
      "story",
      "Once upon a time.",
    ]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("keeps a partial that only happens to start an older answer", () => {
    const history = [
      message("user", "what do you do?"),
      message("assistant", "I work on RAG systems."),
      message("user", "and before?"),
    ];
    const optimistic = [
      message("user", "and before?"),
      message("assistant", "I"),
    ];

    expect(contents(mergeMessages(history, optimistic, STOPPED))).toEqual([
      "what do you do?",
      "I work on RAG systems.",
      "and before?",
      "I",
    ]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("keeps the partial when the saved reply only contains it later", () => {
    const history = [
      message("user", "story"),
      message("assistant", "xx Once upon a time"),
    ];
    const optimistic = [
      message("user", "story"),
      message("assistant", "Once upon"),
    ];

    expect(contents(mergeMessages(history, optimistic, STOPPED))).toEqual([
      "story",
      "xx Once upon a time",
      "Once upon",
    ]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("matches any saved reply after the question, even a one-letter part", () => {
    const history = [
      message("user", "story"),
      message("assistant", "Sorry, I couldn't answer that one."),
      message("assistant", "Once upon a time."),
    ];
    const optimistic = [message("user", "story"), message("assistant", "O")];

    expect(contents(mergeMessages(history, optimistic, STOPPED))).toEqual(
      contents(history),
    );
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("keeps everything while the question itself is not saved yet", () => {
    const history = [message("assistant", "Once upon a time.")];
    const optimistic = [message("user", "story"), message("assistant", "Once")];

    expect(contents(mergeMessages(history, optimistic, STOPPED))).toEqual([
      "Once upon a time.",
      "story",
      "Once",
    ]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("never hides a reply that is still being written", () => {
    const history = [
      message("user", "story"),
      message("assistant", "Once upon a time."),
    ];
    const optimistic = [message("user", "story"), message("assistant", "Once")];

    expect(contents(mergeMessages(history, optimistic, STREAMING))).toEqual([
      "story",
      "Once upon a time.",
      "Once",
    ]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("never binds a repeated question to its older copy in the history", () => {
    const history = [
      message("user", "story"),
      message("assistant", "Once upon a time, long ago."),
    ];
    const optimistic = [
      { ...message("user", "story"), id: "user-2" },
      message("assistant", "Once"),
    ];

    expect(
      contents(
        mergeMessages(history, optimistic, { stopped: true, turnStart: 2 }),
      ),
    ).toEqual(["story", "Once upon a time, long ago.", "story", "Once"]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("matches the repeated question once its new copy is saved", () => {
    const history = [
      message("user", "story"),
      message("assistant", "Once upon a time, long ago."),
      { ...message("user", "story"), id: "u2" },
      message("assistant", "Once more, a new tale."),
    ];
    const optimistic = [
      { ...message("user", "story"), id: "user-2" },
      message("assistant", "Once more"),
    ];

    expect(
      contents(
        mergeMessages(history, optimistic, { stopped: true, turnStart: 2 }),
      ),
    ).toEqual(contents(history));
  });
});
