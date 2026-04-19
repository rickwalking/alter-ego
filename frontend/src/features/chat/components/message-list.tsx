"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { type Message } from "@/schemas/chat";
import { MessageItem } from "./message-item";

interface MessageListProps {
  messages: Message[];
}

export function MessageList({ messages }: MessageListProps) {
  const t = useTranslations("chat");
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex h-full items-center justify-center text-[var(--color-muted-foreground)]" role="status">
        <p>{t("empty")}</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col" role="log" aria-label="Chat messages" aria-live="polite">
      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
