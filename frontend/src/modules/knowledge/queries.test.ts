import { beforeEach, describe, expect, it, vi } from "vitest";
import { skipToken } from "@tanstack/react-query";
import { API_ENDPOINTS } from "@/constants/api";
import { documentKeys, documentOptions, documentsOptions } from "./queries";
import {
  documentListResponseSchema,
  documentSchema,
} from "@/schemas/knowledge";

vi.mock("@/lib/api-client", () => ({
  apiCall: vi.fn(),
}));

import { apiCall } from "@/lib/api-client";

const mockApiCall = vi.mocked(apiCall);
const DOCUMENT_ID = "doc-1";

beforeEach(() => {
  vi.clearAllMocks();
});

function callQueryFn(options: { queryFn?: unknown }): Promise<unknown> {
  expect(options.queryFn).toBeTypeOf("function");
  return (options.queryFn as () => Promise<unknown>)();
}

describe("documentKeys", () => {
  it("returns stable list and detail keys", () => {
    expect(documentKeys.list()).toEqual(["documents"]);
    expect(documentKeys.detail(DOCUMENT_ID)).toEqual(["document", DOCUMENT_ID]);
    expect(documentKeys.detail(null)).toEqual(["document", null]);
  });
});

describe("documentsOptions", () => {
  // Scenario: Display knowledge base interface
  it("fetches the document list and returns only its items", async () => {
    const items = [{ id: DOCUMENT_ID }];
    mockApiCall.mockResolvedValueOnce({ items, total: 1 });

    const options = documentsOptions();
    const result = await callQueryFn(options);

    expect(options.queryKey).toEqual(["documents"]);
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.DOCUMENTS,
      documentListResponseSchema,
    );
    expect(result).toBe(items);
  });
});

describe("documentOptions", () => {
  it("fetches a single document by id", async () => {
    const document = { id: DOCUMENT_ID };
    mockApiCall.mockResolvedValueOnce(document);

    const options = documentOptions(DOCUMENT_ID);
    const result = await callQueryFn(options);

    expect(options.queryKey).toEqual(["document", DOCUMENT_ID]);
    expect(mockApiCall).toHaveBeenCalledWith(
      API_ENDPOINTS.DOCUMENT_BY_ID(DOCUMENT_ID),
      documentSchema,
    );
    expect(result).toBe(document);
  });

  it("skips the query when no id is given", () => {
    const options = documentOptions(null);
    expect(options.queryFn).toBe(skipToken);
    expect(mockApiCall).not.toHaveBeenCalled();
  });
});
