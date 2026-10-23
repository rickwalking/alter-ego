import {
  infiniteQueryOptions,
  queryOptions,
  skipToken,
} from "@tanstack/react-query";
import { API_ENDPOINTS } from "@/constants/api";
import { CONVERSATION_ORIGIN_FILTER_ALTER_EGO } from "@/constants/publish-chat";
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
        `${API_ENDPOINTS.CONVERSATIONS}?origin=${CONVERSATION_ORIGIN_FILTER_ALTER_EGO}`,
        conversationListResponseSchema,
      );
      return result.items;
    },
  });
}

/** Conversations the sidebar loads per page ("Show more" loads the next). */
export const CONVERSATION_PAGE_SIZE = 20;

/** Most conversations one server-side title search returns. */
export const CONVERSATION_SEARCH_LIMIT = 100;

function conversationListUrl(params: Record<string, string>): string {
  const query = new URLSearchParams({
    origin: CONVERSATION_ORIGIN_FILTER_ALTER_EGO,
    ...params,
  });
  return `${API_ENDPOINTS.CONVERSATIONS}?${query.toString()}`;
}

/** The owner's conversations, newest first, a page at a time. */
export function conversationPagesOptions() {
  return infiniteQueryOptions({
    queryKey: [...chatKeys.conversations(), "pages"] as const,
    initialPageParam: 0,
    queryFn: ({ pageParam }) =>
      apiCall<ConversationListResponse>(
        conversationListUrl({
          limit: String(CONVERSATION_PAGE_SIZE),
          offset: String(pageParam),
        }),
        conversationListResponseSchema,
      ),
    getNextPageParam: (last) => {
      const next = last.offset + last.items.length;
      return next < last.total ? next : undefined;
    },
  });
}

/** The owner's conversations whose title contains ``term`` (server-side). */
export function conversationSearchOptions(term: string) {
  return queryOptions({
    queryKey: [...chatKeys.conversations(), "search", term] as const,
    queryFn: term
      ? async () => {
          const result = await apiCall<ConversationListResponse>(
            conversationListUrl({
              limit: String(CONVERSATION_SEARCH_LIMIT),
              search: term,
            }),
            conversationListResponseSchema,
          );
          return result.items;
        }
      : skipToken,
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
