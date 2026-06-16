import { z } from "zod";

export const messageSourceSchema = z.object({
  document_id: z.string(),
  document_title: z.string(),
  content: z.string(),
  score: z.number(),
});

export const messageSchema = z.object({
  id: z.string(),
  role: z.enum(["user", "assistant", "system"]),
  content: z.string(),
  sources: z.unknown().optional(),
  created_at: z.string(),
});

export const conversationSchema = z.object({
  id: z.string(),
  title: z.string().nullable(),
  metadata: z.unknown(),
  created_at: z.string(),
  updated_at: z.string(),
});

export const conversationListResponseSchema = z.object({
  items: z.array(conversationSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export const messageListResponseSchema = z.object({
  items: z.array(messageSchema),
  conversation_id: z.string(),
});

export const chatRequestSchema = z.object({
  content: z.string().min(1).max(10000),
});

export const chatResponseSchema = z.object({
  content: z.string(),
  sources: z.unknown().optional(),
  conversation_id: z.string(),
});

export type MessageSource = z.infer<typeof messageSourceSchema>;
export type Message = z.infer<typeof messageSchema>;
export type Conversation = z.infer<typeof conversationSchema>;
export type ConversationListResponse = z.infer<
  typeof conversationListResponseSchema
>;
export type MessageListResponse = z.infer<typeof messageListResponseSchema>;
export type ChatRequest = z.infer<typeof chatRequestSchema>;
export type ChatResponse = z.infer<typeof chatResponseSchema>;
