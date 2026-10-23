import type { Message } from "@/schemas/chat";

const USER_ROLE: Message["role"] = "user";
const ASSISTANT_ROLE: Message["role"] = "assistant";

/** How the turn on screen relates to the persisted history. */
export interface TurnMerge {
  /** Streaming is over, so a stopped part may give way to the saved reply. */
  stopped: boolean;
  /** History length when this turn started: older rows never match it. */
  turnStart: number;
}

/**
 * The saved replies to this turn: the assistant messages after the saved copy
 * of the turn's own question (looked up only among rows saved since the turn
 * began). Older answers never count, even to the same question asked again.
 */
function repliesToThisTurn(
  turnHistory: readonly Message[],
  optimisticMessages: readonly Message[],
): string[] {
  const question = optimisticMessages.findLast(
    (message) => message.role === USER_ROLE,
  );
  if (!question) return [];
  const asked = turnHistory.findLastIndex(
    (message) =>
      message.role === USER_ROLE && message.content === question.content,
  );
  if (asked === -1) return [];
  return turnHistory
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
 * flight, minus those the history saved since the turn began (an older row
 * with the same text, such as the same question asked earlier, never hides
 * one). A stopped part is dropped only once streaming is over: a reply still
 * being written is never hidden.
 */
export function mergeMessages(
  historyMessages: Message[],
  optimisticMessages: Message[],
  turn: TurnMerge,
): Message[] {
  if (optimisticMessages.length === 0) {
    return historyMessages;
  }
  const turnHistory = historyMessages.slice(turn.turnStart);
  const seen = new Set(
    turnHistory.map((message) => `${message.role}:${message.content}`),
  );
  const savedReplies = turn.stopped
    ? repliesToThisTurn(turnHistory, optimisticMessages)
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
