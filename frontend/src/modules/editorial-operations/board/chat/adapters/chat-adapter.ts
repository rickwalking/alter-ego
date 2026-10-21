import {
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_CYAN_DIM,
  DASHBOARD_CHAT_MAGENTA,
  DASHBOARD_CHAT_MAGENTA_DIM,
  DASHBOARD_CHAT_TEAL,
  DASHBOARD_CHAT_TEAL_DIM,
} from "@/modules/editorial-operations/board/chat/constants";
import type {
  DashboardChatMessage,
  DashboardConversation,
} from "@/modules/editorial-operations/board/chat/types";
import { formatLocaleRelative, formatLocaleTime } from "@/lib/locale-format";
import { firstNonBlank } from "@/lib/utils";
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

/** AE-0417: `locale` is the active UI locale; times are formatted in it. */
export function mapConversationToDashboard(
  conversation: Conversation,
  index: number,
  locale: string,
): DashboardConversation {
  const palette =
    AVATAR_PALETTE[index % AVATAR_PALETTE.length] ?? AVATAR_PALETTE[0];
  const title = firstNonBlank([conversation.title, "New conversation"]);

  return {
    id: conversation.id,
    name: title,
    preview: title,
    time: formatLocaleRelative(conversation.updated_at, locale),
    unread: false,
    avatar: palette.avatar,
    bg: palette.bg,
    color: palette.color,
  };
}

export function mapMessageToDashboard(
  message: Message,
  locale: string,
): DashboardChatMessage {
  const role = message.role === "user" ? "user" : "assistant";
  return {
    role,
    text: message.content,
    time: formatLocaleTime(message.created_at, locale),
  };
}
