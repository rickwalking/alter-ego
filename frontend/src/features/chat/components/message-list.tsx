"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { type Message } from "@/schemas/chat";
import { MessageItem } from "./message-item";
import { TypingIndicator } from "./typing-indicator";

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
}

export function MessageList({ messages, isStreaming = false }: MessageListProps) {
  const t = useTranslations("chat");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isStreaming]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="flex h-full items-center justify-center text-[var(--color-muted-foreground)]" role="status">
        <p>{t("empty")}</p>
      </div>
    );
  }

  const lastMessageIsUser = messages.length > 0 && messages[messages.length - 1]?.role === "user";
  const showTyping = isStreaming && lastMessageIsUser;

  return (
    <div className="flex flex-col" role="log" aria-label="Chat messages" aria-live="polite">
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
      {showTyping && <TypingIndicator />}
      <div ref={bottomRef} />
    </div>
  );
}
