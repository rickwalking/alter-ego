import { describe, it, expect } from "vitest";
import { mapDocumentToCardProps } from "@/features/knowledge/adapters/document-adapter";
import type { Document } from "@/schemas/knowledge";

describe("mapDocumentToCardProps", () => {
  const baseDoc: Document = {
    id: "doc-1",
    title: "Test Doc",
    status: "completed",
    metadata: {},
    chunk_count: 5,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-02T00:00:00Z",
  };

  it("maps completed status to green badge", () => {
    const result = mapDocumentToCardProps(baseDoc);
    expect(result.badgeVariant).toBe("green");
    expect(result.badgeText).toBe("completed");
  });

  it("maps processing status to amber badge", () => {
    const result = mapDocumentToCardProps({
      ...baseDoc,
      status: "processing",
    });
    expect(result.badgeVariant).toBe("amber");
  });

  it("maps unknown status to amber badge", () => {
    const result = mapDocumentToCardProps({
      ...baseDoc,
      status: "unknown",
    });
    expect(result.badgeVariant).toBe("amber");
  });
});
