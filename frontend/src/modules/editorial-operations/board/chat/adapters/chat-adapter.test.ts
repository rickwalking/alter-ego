import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
  mapConversationToDashboard,
  mapMessageToDashboard,
} from "@/modules/editorial-operations/board/chat/adapters/chat-adapter";
import type { Conversation, Message } from "@/schemas/chat";

const NOW = new Date(2026, 9, 17, 17, 5);
const THREE_HOURS_AGO = new Date(2026, 9, 17, 14, 5);

function makeConversation(overrides: Partial<Conversation>): Conversation {
  return {
    id: "conv-1",
    title: "Pauta de outubro",
    metadata: {},
    created_at: THREE_HOURS_AGO.toISOString(),
    updated_at: THREE_HOURS_AGO.toISOString(),
    ...overrides,
  };
}

describe("chat adapter times (AE-0417)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(NOW);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  /** Scenario: Chat conversations show relative times in the active locale */
  it("shows a conversation's last update relative to now, per locale", () => {
    const conversation = makeConversation({});
    expect(
      mapConversationToDashboard(conversation, "pt", "Nova conversa").time,
    ).toBe("há 3 h");
    expect(
      mapConversationToDashboard(conversation, "en", "New conversation").time,
    ).toBe("3h ago");
  });

  /** Scenario: Conversations show their real titles and no invented avatars */
  it("uses the title, falls back to the untitled label, and has no avatar", () => {
    const untitled = mapConversationToDashboard(
      makeConversation({ title: "  " }),
      "pt",
      "Nova conversa",
    );
    expect(untitled).toEqual({
      id: "conv-1",
      name: "Nova conversa",
      time: "há 3 h",
    });
    expect(
      mapConversationToDashboard(makeConversation({}), "pt", "x").name,
    ).toBe("Pauta de outubro");
  });

  it("shows a message's clock time per locale", () => {
    const message: Message = {
      id: "msg-1",
      role: "assistant",
      content: "Olá",
      created_at: THREE_HOURS_AGO.toISOString(),
    };
    expect(mapMessageToDashboard(message, "pt")).toEqual({
      role: "assistant",
      text: "Olá",
      time: "14:05",
    });
    expect(mapMessageToDashboard(message, "en").time).toMatch(/^2:05\sPM$/);
  });
});
