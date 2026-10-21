import { describe, it, expect } from "vitest";
import { mapDocumentToCardProps } from "@/modules/knowledge/adapters/document-adapter";
import type { Document } from "@/schemas/knowledge";

const BASE_DOC: Document = {
  id: "doc-1",
  title: "Test Doc",
  status: "completed",
  scope: "personal",
  is_public: false,
  metadata: {},
  chunk_count: 5,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-02T00:00:00Z",
};

describe("mapDocumentToCardProps status mapping", () => {
  // Scenario: Display knowledge base interface
  it.each([
    ["completed", "green"],
    ["processing", "amber"],
    ["pending", "cyan"],
    ["failed", "red"],
  ])("maps %s to the %s badge", (status, variant) => {
    const result = mapDocumentToCardProps({ ...BASE_DOC, status });
    expect(result).toEqual({
      accent: "cyan",
      badgeVariant: variant,
      badgeText: status,
    });
  });

  it("falls back to amber and echoes an unknown status", () => {
    expect(mapDocumentToCardProps({ ...BASE_DOC, status: "queued" })).toEqual({
      accent: "cyan",
      badgeVariant: "amber",
      badgeText: "queued",
    });
  });
});
