import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiCall } from "@/lib/api-client";
import {
  conversationSchema,
  messageSchema,
  chatResponseSchema,
  conversationListResponseSchema,
  messageListResponseSchema,
  type Conversation,
  type Message,
  type ChatResponse,
  type ConversationListResponse,
  type MessageListResponse,
} from "@/schemas/chat";

const CONVERSATIONS_KEY = "conversations";

export function useConversations() {
  return useQuery({
    queryKey: [CONVERSATIONS_KEY],
    queryFn: async () => {
      const result = await apiCall<ConversationListResponse>(
        "/api/conversations",
        conversationListResponseSchema
      );
      return result.items;
    },
  });
}

export function useConversation(conversationId: string | null) {
  return useQuery({
    queryKey: ["conversation", conversationId],
    queryFn: async () => {
      return apiCall<Conversation>(
        `/api/conversations/${conversationId}`,
        conversationSchema
      );
    },
    enabled: !!conversationId,
  });
}

export function useConversationMessages(conversationId: string | null) {
  return useQuery({
    queryKey: ["messages", conversationId],
    queryFn: async () => {
      const result = await apiCall<MessageListResponse>(
        `/api/conversations/${conversationId}/messages`,
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
      return apiCall<Conversation>("/api/conversations", conversationSchema, {
        method: "POST",
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
        `/api/conversations/${conversationId}/chat`,
        chatResponseSchema,
        {
          method: "POST",
          body: JSON.stringify({ content }),
        }
      );
    },
    onSuccess: (_, { conversationId }) => {
      queryClient.invalidateQueries({ queryKey: ["messages", conversationId] });
      queryClient.invalidateQueries({ queryKey: [CONVERSATIONS_KEY] });
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (conversationId: string) => {
      await fetch(`/api/conversations/${conversationId}`, { method: "DELETE" });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: [CONVERSATIONS_KEY] });
    },
  });
}
