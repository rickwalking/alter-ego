"use client";

import { useTranslations } from "next-intl";
import { User, Bot, BookOpen } from "lucide-react";
import { cn } from "@/lib/utils";
import { type Message } from "@/schemas/chat";

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  const t = useTranslations("chat");
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-4 p-6",
        isUser ? "bg-[var(--color-background)]" : "bg-[var(--color-muted)]",
      )}
    >
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border shadow",
          isUser
            ? "bg-[var(--color-background)]"
            : "bg-[var(--color-primary)] text-[var(--color-primary-foreground)]",
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      <div className="flex-1 space-y-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold">
            {isUser ? t("you") : t("assistant")}
          </span>
          <span className="text-xs text-[var(--color-muted-foreground)]">
            {new Date(message.created_at).toLocaleTimeString()}
          </span>
        </div>
        <div className="prose prose-sm max-w-none dark:prose-invert">
          {message.content}
        </div>
        {Array.isArray(message.sources) && message.sources.length > 0 && (
          <div className="mt-3 space-y-2">
            <div className="flex items-center gap-1 text-xs font-medium text-[var(--color-muted-foreground)]">
              <BookOpen className="h-3 w-3" />
              {t("sources")}
            </div>
            <div className="flex flex-wrap gap-2">
              {message.sources.map((source, i) => (
                <span
                  key={i}
                  className="inline-flex items-center gap-1 rounded-full border border-[var(--color-border)] bg-[var(--color-background)] px-2 py-1 text-xs text-[var(--color-muted-foreground)]"
                  title={source.content}
                >
                  {source.document_title}
                  <span className="text-[var(--color-primary)]">
                    {(source.score * 100).toFixed(0)}%
                  </span>
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
