"use client";

import type { DashboardChatMessage } from "@/modules/editorial-operations";
import { useState } from "react";
import { useTranslations } from "next-intl";
import { useStickToBottom } from "@/lib/use-stick-to-bottom";
import { ChatEmptyState } from "./chat-empty-state";
import { ChatMessageRow, TypingIndicator } from "./chat-message-row";

export interface ChatMessageListProps {
  messages: DashboardChatMessage[];
  isStreaming?: boolean;
  /** Shows the intro and suggested questions on an empty chat; sends the pick. */
  onSuggestion?: (text: string) => void;
}

/** Longest stretch of a finished reply read out by the live region. */
const ANNOUNCED_REPLY_MAX_CHARS = 280;
const MARKDOWN_MARKERS = /[*_#`>[\]()~|]+/g;
/** A markdown link or image: only its text is read, never the address. */
const MARKDOWN_LINK = /!?\[([^\]]{0,200})\]\([^)\s]{0,500}\)/g;

/** The reply as a screen reader should hear it: no markdown, kept short. */
function speakable(text: string): string {
  const plain = text
    .replace(MARKDOWN_LINK, "$1")
    .replace(MARKDOWN_MARKERS, "")
    .replace(/\s+/g, " ")
    .trim();
  if (plain.length <= ANNOUNCED_REPLY_MAX_CHARS) return plain;
  return `${plain.slice(0, ANNOUNCED_REPLY_MAX_CHARS).trimEnd()}…`;
}

/**
 * What the polite live region says: "typing" while a reply streams, then the
 * reply that just finished, once. Opening another conversation or loading
 * history announces nothing (only a streaming → done change does).
 */
function useReplyAnnouncement(
  messages: DashboardChatMessage[],
  isStreaming: boolean,
): string {
  const t = useTranslations("chat");
  const [wasStreaming, setWasStreaming] = useState(isStreaming);
  const [finishedReply, setFinishedReply] = useState("");
  if (wasStreaming !== isStreaming) {
    setWasStreaming(isStreaming);
    const last = messages.at(-1);
    const justFinished = wasStreaming && last?.role === "assistant";
    setFinishedReply(justFinished ? speakable(last.text) : "");
  }
  if (isStreaming) return t("typing");
  return finishedReply ? t("replyAnnounced", { text: finishedReply }) : "";
}

/** Scroll keys: any growth of the list, and whether a turn is in flight. */
function scrollKeys(
  messages: DashboardChatMessage[],
  isStreaming: boolean,
): { contentKey: string; sending: boolean } {
  const lastText = messages.at(-1)?.text ?? "";
  return {
    contentKey: `${messages.length}:${lastText.length}`,
    sending: isStreaming,
  };
}

export function ChatMessageList({
  messages,
  isStreaming = false,
  onSuggestion,
}: Readonly<ChatMessageListProps>): React.ReactElement {
  const t = useTranslations("chat");
  const listRef = useStickToBottom<HTMLDivElement>(
    scrollKeys(messages, isStreaming),
  );
  const announcement = useReplyAnnouncement(messages, isStreaming);
  return (
    <>
      <div
        ref={listRef}
        data-testid="chat-message-list"
        role="log"
        aria-label={t("logLabel")}
        aria-live="off"
        style={{ flex: 1, overflowY: "auto", padding: "24px" }}
      >
        <div className="mx-auto flex w-full max-w-3xl flex-col gap-4">
          {messages.length === 0 && !isStreaming && onSuggestion && (
            <ChatEmptyState onSuggestion={onSuggestion} />
          )}
          {messages.map((msg, index) => (
            <ChatMessageRow key={`${msg.role}-${index}`} msg={msg} />
          ))}
          {isStreaming && <TypingIndicator label={t("typing")} />}
        </div>
        <style>{`
        @keyframes chat-pulse-dot {
          0%, 100% { opacity: 0.35; transform: scale(0.85); }
          50% { opacity: 1; transform: scale(1.15); }
        }
        .chat-typing-dot {
          animation: chat-pulse-dot 1.2s ease-in-out infinite;
        }
        @keyframes chat-empty-in {
          from { opacity: 0; transform: translateY(4px); }
          to { opacity: 1; transform: none; }
        }
        .chat-empty {
          animation: chat-empty-in 240ms cubic-bezier(0.25, 1, 0.5, 1);
        }
        @media (prefers-reduced-motion: reduce) {
          .chat-typing-dot, .chat-empty { animation: none; }
        }
      `}</style>
      </div>
      <p
        role="status"
        className="sr-only"
        aria-live="polite"
        aria-atomic="true"
      >
        {announcement}
      </p>
    </>
  );
}
