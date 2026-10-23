import type { Message } from "@/schemas/chat";

const USER_ROLE: Message["role"] = "user";
const ASSISTANT_ROLE: Message["role"] = "assistant";

/**
 * The saved replies to this turn: the assistant messages after the last saved
 * copy of the turn's own question. Older answers never count, so a short
 * partial that happens to start an earlier answer stays on screen.
 */
function repliesToThisTurn(
  historyMessages: readonly Message[],
  optimisticMessages: readonly Message[],
): string[] {
  const question = optimisticMessages.findLast(
    (message) => message.role === USER_ROLE,
  );
  if (!question) return [];
  const asked = historyMessages.findLastIndex(
    (message) =>
      message.role === USER_ROLE && message.content === question.content,
  );
  if (asked === -1) return [];
  return historyMessages
    .slice(asked + 1)
    .filter((message) => message.role === ASSISTANT_ROLE)
    .map((message) => message.content);
}

/**
 * A reply the user stopped is a prefix of the reply the server saved for the
 * same turn; once that one is in the history the partial copy is dropped.
 */
function isStoppedPartOf(message: Message, savedReplies: string[]): boolean {
  return (
    message.role === ASSISTANT_ROLE &&
    message.content.length > 0 &&
    savedReplies.some((reply) => reply.startsWith(message.content))
  );
}

/**
 * The persisted history followed by the optimistic messages of the turn in
 * flight, minus those the history already holds. A stopped part is dropped
 * only once streaming is over (``stopped``): a reply still being written is
 * never hidden behind an earlier answer to the same question.
 */
export function mergeMessages(
  historyMessages: Message[],
  optimisticMessages: Message[],
  stopped: boolean,
): Message[] {
  if (optimisticMessages.length === 0) {
    return historyMessages;
  }
  const seen = new Set(
    historyMessages.map((message) => `${message.role}:${message.content}`),
  );
  const savedReplies = stopped
    ? repliesToThisTurn(historyMessages, optimisticMessages)
    : [];
  const uniqueOptimistic = optimisticMessages.filter(
    (message) =>
      !seen.has(`${message.role}:${message.content}`) &&
      !isStoppedPartOf(message, savedReplies),
  );
  return [...historyMessages, ...uniqueOptimistic];
}

/** Drop a trailing user message that never got a reply (a failed turn). */
function dropUnansweredUserTurn(prev: Message[]): Message[] {
  return prev.at(-1)?.role === USER_ROLE ? prev.slice(0, -1) : prev;
}

/** With history on, an earlier turn lives in the history, not on screen twice. */
function noEarlierTurns(): Message[] {
  return [];
}

/**
 * How a new turn trims the optimistic messages: with history on it starts
 * empty (a stopped or failed turn's copies are in the history); without it,
 * only a failed turn's unanswered question is dropped.
 */
export function optimisticAtTurnStart(
  loadHistory: boolean,
): (prev: Message[]) => Message[] {
  return loadHistory ? noEarlierTurns : dropUnansweredUserTurn;
}
