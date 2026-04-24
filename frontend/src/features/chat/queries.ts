import { queryOptions, skipToken } from "@tanstack/react-query";
import { API_ENDPOINTS } from "@/constants/api";
import { apiCall } from "@/lib/api-client";
import {
  chatResponseSchema,
  conversationListResponseSchema,
  conversationSchema,
  messageListResponseSchema,
  type ChatResponse,
  type Conversation,
  type ConversationListResponse,
  type MessageListResponse,
} from "@/schemas/chat";

export const chatKeys = {
  conversations: () => ["conversations"] as const,
  conversation: (conversationId: string | null) =>
    ["conversation", conversationId] as const,
  messages: (conversationId: string | null) =>
    ["messages", conversationId] as const,
};

export function conversationsOptions() {
  return queryOptions({
    queryKey: chatKeys.conversations(),
    queryFn: async () => {
      const result = await apiCall<ConversationListResponse>(
        API_ENDPOINTS.CONVERSATIONS,
        conversationListResponseSchema,
      );
      return result.items;
    },
  });
}

export function conversationOptions(conversationId: string | null) {
  return queryOptions({
    queryKey: chatKeys.conversation(conversationId),
    queryFn: conversationId
      ? () =>
          apiCall<Conversation>(
            API_ENDPOINTS.CONVERSATION_BY_ID(conversationId),
            conversationSchema,
          )
      : skipToken,
  });
}

export function conversationMessagesOptions(conversationId: string | null) {
  return queryOptions({
    queryKey: chatKeys.messages(conversationId),
    queryFn: conversationId
      ? async () => {
          const result = await apiCall<MessageListResponse>(
            API_ENDPOINTS.CONVERSATION_MESSAGES(conversationId),
            messageListResponseSchema,
          );
          return result.items;
        }
      : skipToken,
  });
}

export function createConversation({
  title,
  metadata,
}: {
  title?: string;
  metadata?: Record<string, unknown>;
}): Promise<Conversation> {
  return apiCall<Conversation>(
    API_ENDPOINTS.CONVERSATIONS,
    conversationSchema,
    {
      method: "POST",
      body: JSON.stringify({ title, metadata }),
    },
  );
}

export function sendConversationMessage({
  conversationId,
  content,
}: {
  conversationId: string;
  content: string;
}): Promise<ChatResponse> {
  return apiCall<ChatResponse>(
    API_ENDPOINTS.CONVERSATION_CHAT(conversationId),
    chatResponseSchema,
    {
      method: "POST",
      body: JSON.stringify({ content }),
    },
  );
}
