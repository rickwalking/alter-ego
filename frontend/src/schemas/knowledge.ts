import { z } from "zod";

export const documentSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.string(),
  metadata: z.unknown(),
  chunk_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
  error_message: z.string().nullable().optional(),
});

export const documentListResponseSchema = z.object({
  items: z.array(documentSchema),
  total: z.number(),
  limit: z.number(),
  offset: z.number(),
});

export const createDocumentRequestSchema = z.object({
  title: z.string().min(1).max(500),
  content: z.string().min(1),
  metadata: z.record(z.unknown()).optional(),
});

export const documentUploadResponseSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.string(),
  metadata: z.unknown(),
  chunk_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
  error_message: z.string().nullable().optional(),
});

export type Document = z.infer<typeof documentSchema>;
export type DocumentListResponse = z.infer<typeof documentListResponseSchema>;
export type CreateDocumentRequest = z.infer<typeof createDocumentRequestSchema>;
export type DocumentUploadResponse = z.infer<
  typeof documentUploadResponseSchema
>;
