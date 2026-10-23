import type {
  DashboardChatMessage,
  DashboardConversation,
} from "@/modules/editorial-operations/board/chat/types";
import { formatLocaleRelative, formatLocaleTime } from "@/lib/locale-format";
import { firstNonBlank } from "@/lib/utils";
import type { Conversation, Message } from "@/schemas/chat";

/**
 * `locale` is the active UI locale; times are formatted in it. A conversation
 * without a title yet shows `untitled` (the backend titles it from its first
 * message).
 */
export function mapConversationToDashboard(
  conversation: Conversation,
  locale: string,
  untitled: string,
): DashboardConversation {
  return {
    id: conversation.id,
    name: firstNonBlank([conversation.title, untitled]),
    time: formatLocaleRelative(conversation.updated_at, locale),
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
