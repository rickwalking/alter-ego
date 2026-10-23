/**
 * Gherkin: tests/features/chat-polish.feature
 */
import { describe, expect, it } from "vitest";

import type { Message } from "@/schemas/chat";
import { TURN_CLOCK_SKEW_MS } from "../constants";
import { mergeMessages } from "./merge-messages";

const ASKED = Date.parse("2026-10-23T12:00:00Z");
const MINUTE = 60_000;

function message(role: Message["role"], content: string, at: number): Message {
  return {
    id: `${role}-${content}-${String(at)}`,
    role,
    content,
    sources: [],
    created_at: new Date(at).toISOString(),
  };
}

const contents = (messages: Message[]): string[] =>
  messages.map((m) => m.content);

const question = (content = "story"): Message => ({
  ...message("user", content, ASKED),
  id: "user-1",
});
const partial = (content: string): Message => ({
  ...message("assistant", content, ASKED),
  id: "stream-1",
});

describe("mergeMessages", () => {
  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("drops the stopped part once this question's reply is saved", () => {
    const history = [
      message("user", "story", ASKED + 1000),
      message("assistant", "Once upon a time.", ASKED + 5000),
    ];

    expect(
      contents(
        mergeMessages(history, [question(), partial("Once upon")], true),
      ),
    ).toEqual(["story", "Once upon a time."]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("keeps a partial that only happens to start an older answer", () => {
    const history = [
      message("user", "what do you do?", ASKED - 10 * MINUTE),
      message("assistant", "I work on RAG systems.", ASKED - 10 * MINUTE),
      message("user", "and before?", ASKED + 1000),
    ];

    expect(
      contents(
        mergeMessages(history, [question("and before?"), partial("I")], true),
      ),
    ).toEqual([
      "what do you do?",
      "I work on RAG systems.",
      "and before?",
      "I",
    ]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("never binds a repeated question to its older copy", () => {
    const history = [
      message("user", "story", ASKED - 10 * MINUTE),
      message("assistant", "Once upon a time, long ago.", ASKED - 10 * MINUTE),
    ];

    expect(
      contents(mergeMessages(history, [question(), partial("Once")], true)),
    ).toEqual(["story", "Once upon a time, long ago.", "story", "Once"]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("matches the repeated question once its new copy is saved", () => {
    const history = [
      message("user", "story", ASKED - 10 * MINUTE),
      message("assistant", "Once upon a time, long ago.", ASKED - 10 * MINUTE),
      message("user", "story", ASKED + 1000),
      message("assistant", "Once more, a new tale.", ASKED + 5000),
    ];

    expect(
      contents(
        mergeMessages(history, [question(), partial("Once more")], true),
      ),
    ).toEqual(contents(history));
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("allows the server clock to run behind the browser's", () => {
    const history = [
      message("user", "story", ASKED - TURN_CLOCK_SKEW_MS + 1000),
      message(
        "assistant",
        "Once upon a time.",
        ASKED - TURN_CLOCK_SKEW_MS + 2000,
      ),
    ];

    expect(
      contents(mergeMessages(history, [question(), partial("Once")], true)),
    ).toEqual(["story", "Once upon a time."]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("keeps the partial when the saved reply only contains it later", () => {
    const history = [
      message("user", "story", ASKED + 1000),
      message("assistant", "xx Once upon a time", ASKED + 5000),
    ];

    expect(
      contents(
        mergeMessages(history, [question(), partial("Once upon")], true),
      ),
    ).toEqual(["story", "xx Once upon a time", "Once upon"]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("matches any saved reply after the question, even a one-letter part", () => {
    const history = [
      message("user", "story", ASKED + 1000),
      message("assistant", "Sorry, I couldn't answer that one.", ASKED + 2000),
      message("assistant", "Once upon a time.", ASKED + 3000),
    ];

    expect(
      contents(mergeMessages(history, [question(), partial("O")], true)),
    ).toEqual(contents(history));
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("keeps everything while the question itself is not saved yet", () => {
    const history = [
      message("assistant", "Once upon a time.", ASKED - 10 * MINUTE),
    ];

    expect(
      contents(mergeMessages(history, [question(), partial("Once")], true)),
    ).toEqual(["Once upon a time.", "story", "Once"]);
  });

  /** Scenario: A stopped reply is replaced by the reply saved for the same question */
  it("never hides a reply that is still being written", () => {
    const history = [
      message("user", "story", ASKED + 1000),
      message("assistant", "Once upon a time.", ASKED + 5000),
    ];

    expect(
      contents(mergeMessages(history, [question(), partial("Once")], false)),
    ).toEqual(["story", "Once upon a time.", "Once"]);
  });
});
