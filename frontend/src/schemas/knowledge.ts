import { z } from "zod";

export const documentSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.string(),
  scope: z.string(),
  is_public: z.boolean(),
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
  scope: z.string().optional(),
  is_public: z.boolean().optional(),
  metadata: z.record(z.unknown()).optional(),
});

// Kept as an explicit z.object literal (not aliased to documentSchema) because
// the OpenAPI<->Zod schema-drift gate (AE-0141) statically introspects mapped
// schemas and cannot resolve an alias. Mirrors documentSchema's shape.
export const documentUploadResponseSchema = z.object({
  id: z.string(),
  title: z.string(),
  status: z.string(),
  scope: z.string(),
  is_public: z.boolean(),
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
