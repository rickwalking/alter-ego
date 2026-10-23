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
  type ConversationTarget,
  type UseSseChatOptions,
  type UseSseChatReturn,
} from "./hooks/use-sse-chat";

export {
  CHAT_ERROR_KIND,
  CHAT_FAILURE_STAGE,
  CHAT_LENGTH_COUNTER_RATIO,
  CHAT_MESSAGE_MAX_LENGTH,
  CHAT_SEND_RESULT,
  type ChatErrorKind,
  type ChatSendResult,
} from "./constants";
export { classifyChatError, type ChatFailure } from "./chat-errors";
