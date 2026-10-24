import type { Message } from "@/schemas/chat";
import { TURN_CLOCK_SKEW_MS } from "../constants";

const USER_ROLE: Message["role"] = "user";
const ASSISTANT_ROLE: Message["role"] = "assistant";

/**
 * The history rows saved since this turn's question was sent (allowing for
 * clock skew between the browser and the server). Older rows, such as the
 * same question asked minutes ago, never stand in for this turn.
 */
function rowsOfThisTurn(
  historyMessages: readonly Message[],
  question: Message | undefined,
): Message[] {
  const askedAt = question ? Date.parse(question.created_at) : Number.NaN;
  if (!Number.isFinite(askedAt)) return [];
  const since = askedAt - TURN_CLOCK_SKEW_MS;
  return historyMessages.filter(
    (message) => Date.parse(message.created_at) >= since,
  );
}

/**
 * The saved replies to this turn: the assistant messages after the saved copy
 * of the turn's own question, among the rows saved since it was sent.
 */
function repliesToThisTurn(
  turnHistory: readonly Message[],
  question: Message | undefined,
): string[] {
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
 * flight, minus those the history saved since the turn's question (an older
 * row with the same text, such as the same question asked more than a minute
 * earlier, never hides one; within the clock-skew minute a repeat can be
 * hidden until the history is re-read, never lost). A stopped part is dropped
 * only once streaming is over: a reply still being written is never hidden.
 */
export function mergeMessages(
  historyMessages: Message[],
  optimisticMessages: Message[],
  stopped: boolean,
): Message[] {
  if (optimisticMessages.length === 0) {
    return historyMessages;
  }
  const question = optimisticMessages.findLast(
    (message) => message.role === USER_ROLE,
  );
  const turnHistory = rowsOfThisTurn(historyMessages, question);
  const seen = new Set(
    turnHistory.map((message) => `${message.role}:${message.content}`),
  );
  const savedReplies = stopped ? repliesToThisTurn(turnHistory, question) : [];
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

function keepEverything(prev: Message[]): Message[] {
  return prev;
}

/**
 * How a new turn trims the optimistic messages: with history on it starts
 * empty (an earlier turn's copies are in the history); without it, a stopped
 * turn stays on screen as it was, and only a failed turn's unanswered
 * question is dropped.
 */
export function optimisticAtTurnStart(
  loadHistory: boolean,
  previousTurnStopped: boolean,
): (prev: Message[]) => Message[] {
  if (loadHistory) return noEarlierTurns;
  return previousTurnStopped ? keepEverything : dropUnansweredUserTurn;
}

/**
 * Whether the turn on screen still waits for its saved reply: its question is
 * not in the history yet, or no reply was saved after it.
 */
export function turnStillOpen(
  historyMessages: readonly Message[],
  optimisticMessages: readonly Message[],
): boolean {
  const question = optimisticMessages.findLast(
    (message) => message.role === USER_ROLE,
  );
  if (!question) return false;
  const turnHistory = rowsOfThisTurn(historyMessages, question);
  const asked = turnHistory.findLastIndex(
    (message) =>
      message.role === USER_ROLE && message.content === question.content,
  );
  if (asked === -1) return true;
  return !turnHistory
    .slice(asked + 1)
    .some((message) => message.role === ASSISTANT_ROLE);
}
