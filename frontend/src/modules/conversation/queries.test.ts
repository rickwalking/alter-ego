import { describe, expect, it } from "vitest";
import { chatKeys } from "./queries";

describe("chatKeys", () => {
  it("returns stable keys for conversations, detail, and messages", () => {
    expect(chatKeys.conversations()).toEqual(["conversations"]);
    expect(chatKeys.conversation("conv-1")).toEqual(["conversation", "conv-1"]);
    expect(chatKeys.conversation(null)).toEqual(["conversation", null]);
    expect(chatKeys.messages("conv-1")).toEqual(["messages", "conv-1"]);
    expect(chatKeys.messages(null)).toEqual(["messages", null]);
  });
});
