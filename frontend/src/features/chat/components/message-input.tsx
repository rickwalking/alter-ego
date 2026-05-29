"use client";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTextarea } from "@/components/atoms/neon-textarea";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { Send } from "lucide-react";
import { cn } from "@/lib/utils";

interface MessageInputProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
}

export function MessageInput({ onSend, isLoading = false }: MessageInputProps) {
  const t = useTranslations("chat");
  const [message, setMessage] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (message.trim() && !isLoading) {
      onSend(message.trim());
      setMessage("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e);
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="flex items-end gap-2 p-4 border-t"
      role="form"
      aria-label="Message input"
    >
      <NeonTextarea
        value={message}
        onChange={(e) => setMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={t("input.placeholder")}
        disabled={isLoading}
        rows={1}
        aria-label={t("input.placeholder")}
        className={cn("min-h-[60px] resize-none", isLoading && "opacity-50")}
      />
      <NeonButton
        type="submit"
        size="icon"
        disabled={!message.trim() || isLoading}
        className="h-[60px] w-[60px] shrink-0"
        aria-label={t("input.send")}
      >
        <Send className="h-5 w-5" aria-hidden="true" />
        <span className="sr-only">{t("input.send")}</span>
      </NeonButton>
    </form>
  );
}
