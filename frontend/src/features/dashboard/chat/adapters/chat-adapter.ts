import {
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_CYAN_DIM,
  DASHBOARD_CHAT_MAGENTA,
  DASHBOARD_CHAT_MAGENTA_DIM,
  DASHBOARD_CHAT_TEAL,
  DASHBOARD_CHAT_TEAL_DIM,
} from "@/features/dashboard/chat/constants";
import type {
  DashboardChatMessage,
  DashboardConversation,
} from "@/features/dashboard/chat/types";
import type { Conversation, Message } from "@/schemas/chat";

const AVATAR_PALETTE = [
  { avatar: "AE", bg: DASHBOARD_CHAT_CYAN_DIM, color: DASHBOARD_CHAT_CYAN },
  {
    avatar: "KB",
    bg: DASHBOARD_CHAT_MAGENTA_DIM,
    color: DASHBOARD_CHAT_MAGENTA,
  },
  { avatar: "WF", bg: DASHBOARD_CHAT_TEAL_DIM, color: DASHBOARD_CHAT_TEAL },
] as const;

function formatRelativeTime(iso: string): string {
  const date = new Date(iso);
  const diffMs = Date.now() - date.getTime();
  const diffMins = Math.floor(diffMs / 60_000);
  if (diffMins < 1) return "Just now";
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHours = Math.floor(diffMins / 60);
  if (diffHours < 24) return `${diffHours}h ago`;
  return date.toLocaleDateString();
}

function formatMessageTime(iso: string): string {
  return new Date(iso).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function mapConversationToDashboard(
  conversation: Conversation,
  index: number,
): DashboardConversation {
  const palette = AVATAR_PALETTE[index % AVATAR_PALETTE.length];
  const title = conversation.title?.trim() || "New conversation";

  return {
    id: conversation.id,
    name: title,
    preview: title,
    time: formatRelativeTime(conversation.updated_at),
    unread: false,
    avatar: palette.avatar,
    bg: palette.bg,
    color: palette.color,
  };
}

export function mapMessageToDashboard(message: Message): DashboardChatMessage {
  const role = message.role === "user" ? "user" : "assistant";
  return {
    role,
    text: message.content,
    time: formatMessageTime(message.created_at),
  };
}
