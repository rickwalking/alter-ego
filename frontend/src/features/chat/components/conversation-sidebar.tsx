"use client";

import { useTranslations } from "next-intl";
import { MessageSquare, Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import { type Conversation } from "@/schemas/chat";
import { cn } from "@/lib/utils";

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  isLoading?: boolean;
}

export function ConversationSidebar({
  conversations,
  activeId,
  onNewChat,
  onSelectConversation,
  isLoading,
}: ConversationSidebarProps) {
  const t = useTranslations("chat");

  return (
    <nav className="flex h-full w-64 flex-col border-r bg-[var(--color-muted)]" aria-label={t("sidebar.label")}>
      <div className="p-4">
        <Button onClick={onNewChat} className="w-full gap-2" aria-label={t("input.newChat")}>
          <Plus className="h-4 w-4" aria-hidden="true" />
          {t("input.newChat")}
        </Button>
      </div>

      <div className="flex-1 overflow-auto px-2" role="list" aria-label={t("sidebar.label")}>
        {isLoading ? (
          <div className="space-y-2 p-3" aria-busy="true" aria-label={t("sidebar.loading")}>
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="h-9 animate-pulse rounded-lg bg-[var(--color-accent)]"
                aria-hidden="true"
              />
            ))}
          </div>
        ) : conversations.length === 0 ? (
          <p className="p-4 text-sm text-[var(--color-muted-foreground)]" role="status">
            {t("sidebar.empty")}
          </p>
        ) : (
          <div className="space-y-1">
            {conversations.map((conversation) => (
              <button
                key={conversation.id}
                type="button"
                role="listitem"
                onClick={() => onSelectConversation(conversation.id)}
                aria-current={activeId === conversation.id ? "page" : undefined}
                className={cn(
                  "flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm transition-colors",
                  activeId === conversation.id
                    ? "bg-[var(--color-primary)] text-[var(--color-primary-foreground)]"
                    : "hover:bg-[var(--color-accent)]"
                )}
              >
                <MessageSquare className="h-4 w-4 shrink-0" aria-hidden="true" />
                <span className="truncate">
                  {conversation.title || t("input.newChat")}
                </span>
              </button>
            ))}
          </div>
        )}
      </div>
    </nav>
  );
}
