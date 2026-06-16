/**
 * `conversation` — bounded-context public contract (AE-0139).
 *
 * Owns the chat / conversation surface — conversation CRUD hooks, the SSE
 * streaming chat hook, and the conversation query options — migrated from the
 * legacy `features/chat` folder. This barrel is the ONLY import surface for
 * cross-context and `app/` consumers; everything else under
 * `modules/conversation/**` is internal.
 *
 * See `src/modules/README.md` for the public-contract convention.
 */

/* --- query options / keys --- */
export {
  chatKeys,
  conversationsOptions,
  conversationOptions,
  conversationMessagesOptions,
  createConversation,
  sendConversationMessage,
} from "./queries";

/* --- conversation hooks --- */
export {
  MESSAGES_KEY,
  useConversations,
  useConversation,
  useConversationMessages,
  useCreateConversation,
  useSendMessage,
  useDeleteConversation,
} from "./hooks/use-chat";

/* --- SSE streaming chat hook --- */
export {
  useSseChat,
  type UseSseChatOptions,
  type UseSseChatReturn,
} from "./hooks/use-sse-chat";
