import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiCall, apiCallNoContent } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import {
  conversationSchema,
  chatResponseSchema,
  conversationListResponseSchema,
  messageListResponseSchema,
  type Conversation,
  type ChatResponse,
  type ConversationListResponse,
  type MessageListResponse,
} from "@/schemas/chat";

const CONVERSATIONS_KEY = "conversations";
const CONVERSATION_KEY = "conversation";
const MESSAGES_KEY = "messages";

export function useConversations() {
  return useQuery({
    queryKey: [CONVERSATIONS_KEY],
    queryFn: async () => {
      const result = await apiCall<ConversationListResponse>(
        API_ENDPOINTS.CONVERSATIONS,
        conversationListResponseSchema
      );
      return result.items;
    },
  });
}

export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: [CONVERSATION_KEY, conversationId],
    queryFn: async () => {
      return apiCall<Conversation>(
        API_ENDPOINTS.CONVERSATION_BY_ID(conversationId as string),
        conversationSchema
      );
    },
    enabled: !!conversationId,
  });
}

export function useConversationMessages(conversationId: string | null) {
  return useQuery({
    queryKey: [MESSAGES_KEY, conversationId],
    queryFn: async () => {
      const result = await apiCall<MessageListResponse>(
        API_ENDPOINTS.CONVERSATION_MESSAGES(conversationId as string),
        messageListResponseSchema
      );
      return result.items;
    },
    enabled: !!conversationId,
  });
}

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ title, metadata }: { title?: string; metadata?: Record<string, unknown> }) => {
      return apiCall<Conversation>(API_ENDPOINTS.CONVERSATIONS, conversationSchema, {
        method: HTTP_METHODS.POST,
        body: JSON.stringify({ title, metadata }),
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CONVERSATIONS_KEY] });
    },
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ conversationId, content }: { conversationId: string; content: string }) => {
      return apiCall<ChatResponse>(
        API_ENDPOINTS.CONVERSATION_CHAT(conversationId),
        chatResponseSchema,
        {
          method: HTTP_METHODS.POST,
          body: JSON.stringify({ content }),
        }
      );
    },
    onSuccess: (_, { conversationId }) => {
      queryClient.invalidateQueries({ queryKey: [MESSAGES_KEY, conversationId] });
      queryClient.invalidateQueries({ queryKey: [CONVERSATIONS_KEY] });
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (conversationId: string) => {
      await apiCallNoContent(API_ENDPOINTS.CONVERSATION_BY_ID(conversationId), {
        method: HTTP_METHODS.DELETE,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CONVERSATIONS_KEY] });
    },
  });
}
