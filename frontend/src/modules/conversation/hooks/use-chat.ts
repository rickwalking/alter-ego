import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiCallNoContent } from "@/lib/api-client";
import { API_ENDPOINTS, HTTP_METHODS } from "@/constants/api";
import { type Conversation } from "@/schemas/chat";
import {
  chatKeys,
  conversationMessagesOptions,
  conversationOptions,
  conversationsOptions,
  createConversation,
  sendConversationMessage,
} from "@/modules/conversation/queries";

export const MESSAGES_KEY = chatKeys.messages(null)[0];

export function useConversations() {
  return useQuery(conversationsOptions());
}

export function useConversation(conversationId: string | null) {
  return useQuery(conversationOptions(conversationId));
}

export function useConversationMessages(conversationId: string | null) {
  return useQuery(conversationMessagesOptions(conversationId));
}

export function useCreateConversation() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: createConversation,
    onSuccess: (conversation) => {
      queryClient.setQueryData(
        chatKeys.conversation(conversation.id),
        conversation,
      );
      queryClient.setQueryData<Conversation[]>(
        chatKeys.conversations(),
        (previous) =>
          previous
            ? [
                conversation,
                ...previous.filter((item) => item.id !== conversation.id),
              ]
            : previous,
      );
      void queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
    onError: (error) => {
      console.error("Failed to create conversation:", error);
    },
  });
}

export function useSendMessage() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: sendConversationMessage,
    onSuccess: (_, { conversationId }) => {
      void queryClient.invalidateQueries({
        queryKey: chatKeys.messages(conversationId),
      });
      void queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
    onError: (error) => {
      console.error("Failed to send message:", error);
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
    onSuccess: (_, conversationId) => {
      queryClient.setQueryData<Conversation[]>(
        chatKeys.conversations(),
        (previous) =>
          previous?.filter(
            (conversation) => conversation.id !== conversationId,
          ),
      );
      queryClient.removeQueries({
        queryKey: chatKeys.conversation(conversationId),
      });
      queryClient.removeQueries({
        queryKey: chatKeys.messages(conversationId),
      });
      void queryClient.invalidateQueries({ queryKey: chatKeys.conversations() });
    },
    onError: (error) => {
      console.error("Failed to delete conversation:", error);
    },
  });
}
