/**
 * `conversation` — bounded-context public contract.
 *
 * Owns the chat / conversation surface — conversation CRUD hooks, the SSE
 * streaming chat hook, and the conversation query options — migrated from the
 * legacy `features/chat` folder. This barrel is the ONLY import surface for
 * cross-context and `app/` consumers; everything else under
 * `modules/conversation/**` is internal.
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

export {
  chatKeys,
  conversationsOptions,
  conversationOptions,
  conversationMessagesOptions,
  createConversation,
  sendConversationMessage,
} from "./queries";

export {
  MESSAGES_KEY,
  useConversations,
  useConversation,
  useConversationMessages,
  useCreateConversation,
  useSendMessage,
  useDeleteConversation,
} from "./hooks/use-chat";

export {
  useSseChat,
  type UseSseChatOptions,
  type UseSseChatReturn,
} from "./hooks/use-sse-chat";
