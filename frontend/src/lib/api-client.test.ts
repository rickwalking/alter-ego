import { describe, it, expect, vi } from "vitest";
import {
  apiCall,
  apiCallNoContent,
  ApiError,
  apiResponseSchema,
  errorResponseSchema,
} from "./api-client";
import { z } from "zod";

describe("API Client Module", () => {
  describe("Given the apiCall function", () => {
    const testSchema = z.object({
      id: z.string(),
      name: z.string(),
    });

    describe("When the API call is successful", () => {
      it("Then it should return the validated data", async () => {
        const mockData = { id: "1", name: "Test" };
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            success: true,
            data: mockData,
          }),
        } as Response));

        const result = await apiCall("/api/test", testSchema);
        expect(result).toEqual(mockData);
        vi.unstubAllGlobals();
      });

      it("Then it should include Content-Type header by default", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            success: true,
            data: { id: "1", name: "Test" },
          }),
        } as Response);
        vi.stubGlobal("fetch", mockFetch);

        await apiCall("/api/test", testSchema);

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/test",
          expect.objectContaining({
            headers: expect.objectContaining({
              "Content-Type": "application/json",
            }),
          })
        );
        vi.unstubAllGlobals();
      });

      it("Then it should merge custom headers", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            success: true,
            data: { id: "1", name: "Test" },
          }),
        } as Response);
        vi.stubGlobal("fetch", mockFetch);

        await apiCall("/api/test", testSchema, {
          headers: { Authorization: "Bearer token" },
        });

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/test",
          expect.objectContaining({
            headers: expect.objectContaining({
              "Content-Type": "application/json",
              Authorization: "Bearer token",
            }),
          })
        );
        vi.unstubAllGlobals();
      });

      it("Then it should pass custom options to fetch", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            success: true,
            data: { id: "1", name: "Test" },
          }),
        } as Response);
        vi.stubGlobal("fetch", mockFetch);

        await apiCall("/api/test", testSchema, {
          method: "POST",
          body: JSON.stringify({ test: true }),
        });

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/test",
          expect.objectContaining({
            method: "POST",
            body: JSON.stringify({ test: true }),
          })
        );
        vi.unstubAllGlobals();
      });
    });

    describe("When the API returns an HTTP error", () => {
      it("Then it should throw an ApiError with correct message", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: false,
          status: 404,
          json: async () => ({ message: "Not found", code: "NOT_FOUND" }),
        } as Response));

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(ApiError);
        vi.unstubAllGlobals();
      });

      it("Then the ApiError should include the status code", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
          json: async () => ({ message: "Server error" }),
        } as Response));

        try {
          await apiCall("/api/test", testSchema);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect((error as ApiError).status).toBe(500);
        }
        vi.unstubAllGlobals();
      });

      it("Then the ApiError should include the error code if provided", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: false,
          status: 400,
          json: async () => ({ message: "Bad request", code: "VALIDATION_ERROR" }),
        } as Response));

        try {
          await apiCall("/api/test", testSchema);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect((error as ApiError).code).toBe("VALIDATION_ERROR");
        }
        vi.unstubAllGlobals();
      });

      it("Then it should handle non-JSON error responses", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: false,
          status: 500,
          json: async () => {
            throw new Error("Invalid JSON");
          },
        } as unknown as Response));

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "HTTP error! status: 500"
        );
        vi.unstubAllGlobals();
      });
    });

    describe("When the API response structure is invalid", () => {
      it("Then it should throw an ApiError for missing success field", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({ data: { id: "1", name: "Test" } }),
        } as Response));

        // When the response has no `success` field, apiCall falls through
        // to the direct-schema branch and tries to validate the raw JSON
        // against `testSchema` (expects {id, name} at top level). The
        // actual shape is {data: {id, name}}, so validation fails and we
        // throw with "Invalid data from API".
        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "Invalid data from API"
        );
        vi.unstubAllGlobals();
      });

      it("Then it should throw an ApiError for invalid data structure", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            success: true,
            data: { id: "1" }, // Missing 'name' field
          }),
        } as Response));

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "Invalid data from API"
        );
        vi.unstubAllGlobals();
      });
    });

    describe("When the API returns a success=false response", () => {
      it("Then it should throw an ApiError with the error message", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            success: false,
            error: {
              code: "VALIDATION_FAILED",
              message: "Invalid input data",
            },
          }),
        } as Response));

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "Invalid input data"
        );
        vi.unstubAllGlobals();
      });

      it("Then the error code should be included in the ApiError", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            success: false,
            error: {
              code: "AUTH_REQUIRED",
              message: "Authentication required",
            },
          }),
        } as Response));

        try {
          await apiCall("/api/test", testSchema);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect((error as ApiError).code).toBe("AUTH_REQUIRED");
        }
        vi.unstubAllGlobals();
      });

      it("Then it should handle malformed error responses", async () => {
        vi.stubGlobal("fetch", vi.fn().mockResolvedValue({
          ok: true,
          json: async () => ({
            success: false,
            // Missing error object
          }),
        } as Response));

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "API request failed"
        );
        vi.unstubAllGlobals();
      });
    });
  });

  describe("Given the ApiError class", () => {
    describe("When an ApiError is created", () => {
      it("Then it should be an instance of Error", () => {
        const error = new ApiError(404, "Not found");
        expect(error).toBeInstanceOf(Error);
      });

      it("Then it should have the correct name", () => {
        const error = new ApiError(404, "Not found");
        expect(error.name).toBe("ApiError");
      });

      it("Then it should store the status code", () => {
        const error = new ApiError(500, "Server error");
        expect(error.status).toBe(500);
      });

      it("Then it should store the message", () => {
        const error = new ApiError(400, "Bad request");
        expect(error.message).toBe("Bad request");
      });

      it("Then it should store the error code if provided", () => {
        const error = new ApiError(400, "Bad request", "VALIDATION_ERROR");
        expect(error.code).toBe("VALIDATION_ERROR");
      });
    });
  });

  describe("Given the apiResponseSchema", () => {
    describe("When validating API responses", () => {
      it("Then it should accept valid success responses", () => {
        const valid = {
          success: true,
          data: { id: "1", name: "Test" },
        };
        expect(apiResponseSchema.safeParse(valid).success).toBe(true);
      });

      it("Then it should accept responses with optional message", () => {
        const valid = {
          success: false,
          data: null,
          message: "Error occurred",
        };
        expect(apiResponseSchema.safeParse(valid).success).toBe(true);
      });

      it("Then it should require the success field", () => {
        const invalid = {
          data: { id: "1", name: "Test" },
        };
        expect(apiResponseSchema.safeParse(invalid).success).toBe(false);
      });
    });
  });

  describe("Given the errorResponseSchema", () => {
    describe("When validating error responses", () => {
      it("Then it should accept valid error responses", () => {
        const valid = {
          success: false,
          error: {
            code: "ERROR_CODE",
            message: "Error message",
          },
        };
        expect(errorResponseSchema.safeParse(valid).success).toBe(true);
      });

      it("Then it should accept error responses with optional details", () => {
        const valid = {
          success: false,
          error: {
            code: "ERROR_CODE",
            message: "Error message",
            details: { field: "value" },
          },
        };
        expect(errorResponseSchema.safeParse(valid).success).toBe(true);
      });

      it("Then it should reject responses with success: true", () => {
        const invalid = {
          success: true,
          error: {
            code: "ERROR",
            message: "Error",
          },
        };
        expect(errorResponseSchema.safeParse(invalid).success).toBe(false);
      });

      it("Then it should require the error object", () => {
        const invalid = {
          success: false,
        };
        expect(errorResponseSchema.safeParse(invalid).success).toBe(false);
      });
    });
  });

  describe("Given the apiCallNoContent function", () => {
    describe("When the API returns 204 No Content", () => {
      it("Then it should resolve without a value", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({ ok: true, status: 204 } as Response),
        );

        await expect(
          apiCallNoContent("/api/documents/1", { method: "DELETE" }),
        ).resolves.toBeUndefined();
        vi.unstubAllGlobals();
      });

      it("Then it should pass method and headers through to fetch", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          status: 204,
        } as Response);
        vi.stubGlobal("fetch", mockFetch);

        await apiCallNoContent("/api/documents/1", {
          method: "DELETE",
          headers: { "X-Foo": "bar" },
        });

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/documents/1",
          expect.objectContaining({
            method: "DELETE",
            headers: expect.objectContaining({
              "Content-Type": "application/json",
              "X-Foo": "bar",
            }),
          }),
        );
        vi.unstubAllGlobals();
      });
    });

    describe("When the API returns a 4xx error", () => {
      it("Then it should throw an ApiError with the returned message", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 404,
            json: async () => ({ message: "Document not found" }),
          } as Response),
        );

        await expect(
          apiCallNoContent("/api/documents/missing", { method: "DELETE" }),
        ).rejects.toThrow("Document not found");
        vi.unstubAllGlobals();
      });

      it("Then it should include the HTTP status code on the ApiError", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 403,
            json: async () => ({ message: "forbidden", code: "ACL_DENY" }),
          } as Response),
        );

        try {
          await apiCallNoContent("/api/conversations/1", { method: "DELETE" });
          expect.fail("expected ApiError");
        } catch (err) {
          expect(err).toBeInstanceOf(ApiError);
          expect((err as ApiError).status).toBe(403);
          expect((err as ApiError).code).toBe("ACL_DENY");
        }
        vi.unstubAllGlobals();
      });

      it("Then it should fall back to a generic message when the body isn't JSON", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 500,
            json: async () => {
              throw new Error("not json");
            },
          } as unknown as Response),
        );

        await expect(
          apiCallNoContent("/api/documents/1", { method: "DELETE" }),
        ).rejects.toThrow("HTTP error! status: 500");
        vi.unstubAllGlobals();
      });
    });
  });
});
