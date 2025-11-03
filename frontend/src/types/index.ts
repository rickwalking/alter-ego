/**
 * Message interface for chat messages
 */
export interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: string;
}

/**
 * Request type for sending chat messages to backend
 */
export type ChatRequest = {
  message: string;
};

/**
 * Response type from backend chat API
 */
export type ChatResponse = {
  response: string;
  timestamp: string;
};

/**
 * Theme type for dual theme support
 */
export type Theme = 'cyber-purple' | 'electric-blue';
