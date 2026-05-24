"use client";

import { Bot } from "lucide-react";

export function TypingIndicator() {
  return (
    <div className="flex gap-4 bg-[var(--color-muted)] p-6">
      <div className="flex h-8 w-8 shrink-0 select-none items-center justify-center rounded-md border bg-[var(--color-primary)] text-[var(--color-primary-foreground)] shadow">
        <Bot className="h-4 w-4" />
      </div>
      <div className="flex-1 space-y-2">
        <div className="flex items-center gap-2">
          <span className="font-semibold">Assistant</span>
        </div>
        <div className="flex items-center gap-1" aria-label="Assistant is typing">
          <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-[var(--color-muted-foreground)] [animation-delay:0ms]" />
          <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-[var(--color-muted-foreground)] [animation-delay:150ms]" />
          <span className="inline-block h-2 w-2 animate-bounce rounded-full bg-[var(--color-muted-foreground)] [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}
