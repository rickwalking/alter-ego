import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import {
  apiCall,
  apiCallNoContent,
  apiCallOwnerOnly,
  ApiError,
  apiResponseSchema,
  errorResponseSchema,
} from "./api-client";
import { z } from "zod";

function mockWindowLocation(): { get href(): string; set href(value: string) } {
  let href = "";
  const location = {
    get href() {
      return href;
    },
    set href(value: string) {
      href = value;
    },
  };
  Object.defineProperty(globalThis, "location", {
    value: location,
    writable: true,
    configurable: true,
  });
  return location;
}

describe("API Client Module", () => {
  describe("Given the apiCall function", () => {
    const testSchema = z.object({
      id: z.string(),
      name: z.string(),
    });

    describe("When the API call is successful", () => {
      it("Then it should return the validated data", async () => {
        const mockData = { id: "1", name: "Test" };
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: mockData,
              }),
          }),
        );

        const result = await apiCall("/api/test", testSchema);
        expect(result).toEqual(mockData);
        vi.unstubAllGlobals();
      });

      it("Then it should include Content-Type header by default", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              data: { id: "1", name: "Test" },
            }),
        });
        vi.stubGlobal("fetch", mockFetch);

        await apiCall("/api/test", testSchema);

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/test",
          expect.objectContaining({
            headers: expect.objectContaining({
              "Content-Type": "application/json",
            }) as unknown,
          }),
        );
        vi.unstubAllGlobals();
      });

      it("Then it should merge custom headers", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              data: { id: "1", name: "Test" },
            }),
        });
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
            }) as unknown,
          }),
        );
        vi.unstubAllGlobals();
      });

      it("Then it should validate direct responses without a success wrapper", async () => {
        const mockData = { id: "1", name: "Direct" };
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve(mockData),
          }),
        );

        const result = await apiCall("/api/test", testSchema);
        expect(result).toEqual(mockData);
        vi.unstubAllGlobals();
      });

      it("Then it should include credentials on every request", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              data: { id: "1", name: "Test" },
            }),
        });
        vi.stubGlobal("fetch", mockFetch);

        await apiCall("/api/test", testSchema);

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/test",
          expect.objectContaining({
            credentials: "include",
          }),
        );
        vi.unstubAllGlobals();
      });

      it("Then it should pass custom options to fetch", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () =>
            Promise.resolve({
              success: true,
              data: { id: "1", name: "Test" },
            }),
        });
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
          }),
        );
        vi.unstubAllGlobals();
      });
    });

    describe("When the API returns 401 Unauthorized", () => {
      afterEach(() => {
        vi.unstubAllGlobals();
      });

      it("Then it should throw with the server message", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
            json: () =>
              Promise.resolve({ message: "Session expired", code: "AUTH" }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toMatchObject({
          status: 401,
          message: "Session expired",
          code: "AUTH",
        });
      });

      it("Then it should fall back to Unauthorized when the body is not JSON", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
            json: () => {
              return Promise.reject(new Error("not json"));
            },
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toMatchObject({
          status: 401,
          message: "Unauthorized",
        });
      });

      it("Then it should redirect the browser to the login page", async () => {
        const location = mockWindowLocation();
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
            json: () => Promise.resolve({ message: "Session expired" }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          ApiError,
        );
        expect(location.href).toContain("/auth/logout");
        expect(location.href).not.toContain("/api/");
        expect(location.href).toContain("redirect=");
      });
    });

    describe("When the API returns 403 Forbidden", () => {
      afterEach(() => {
        vi.unstubAllGlobals();
      });

      it("Then it should throw with the server message", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 403,
            json: () =>
              Promise.resolve({
                message: "Access denied",
                code: "ACL_DENY",
              }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toMatchObject({
          status: 403,
          message: "Access denied",
          code: "ACL_DENY",
        });
      });

      it("Then it should fall back to Forbidden when the body is not JSON", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 403,
            json: () => {
              return Promise.reject(new Error("not json"));
            },
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toMatchObject({
          status: 403,
          message: "Forbidden",
        });
      });

      it("Then it should redirect the browser to the forbidden page", async () => {
        const location = mockWindowLocation();
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 403,
            json: () => Promise.resolve({ message: "Access denied" }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          ApiError,
        );
        expect(location.href).toBe("/403");
      });

      // Scenario: An API call refused with password_change_required goes to the change page
      it.each([
        ["apiCall", apiCall],
        ["apiCallOwnerOnly", apiCallOwnerOnly],
      ] as const)(
        "Then a password_change_required 403 from %s goes to the change-password page",
        async (_name, call) => {
          const location = mockWindowLocation();
          vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue({
              ok: false,
              status: 403,
              json: () =>
                Promise.resolve({
                  detail: "Password change required",
                  code: "password_change_required",
                }),
            }),
          );

          await expect(call("/api/test", testSchema)).rejects.toMatchObject({
            status: 403,
            code: "password_change_required",
          });
          expect(location.href).toBe("/dashboard/account/password");
        },
      );
    });

    describe("When the API returns an HTTP error", () => {
      it("Then it should throw an ApiError with correct message", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 404,
            json: () =>
              Promise.resolve({ message: "Not found", code: "NOT_FOUND" }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          ApiError,
        );
        vi.unstubAllGlobals();
      });

      it("Then the ApiError should include the status code", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 500,
            json: () => Promise.resolve({ message: "Server error" }),
          }),
        );

        try {
          await apiCall("/api/test", testSchema);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect((error as ApiError).status).toBe(500);
        }
        vi.unstubAllGlobals();
      });

      it("Then the ApiError should include the error code if provided", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 400,
            json: () =>
              Promise.resolve({
                message: "Bad request",
                code: "VALIDATION_ERROR",
              }),
          }),
        );

        try {
          await apiCall("/api/test", testSchema);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect((error as ApiError).code).toBe("VALIDATION_ERROR");
        }
        vi.unstubAllGlobals();
      });

      it("Then it should handle non-JSON error responses", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 500,
            json: () => {
              return Promise.reject(new Error("Invalid JSON"));
            },
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "HTTP error! status: 500",
        );
        vi.unstubAllGlobals();
      });
    });

    describe("When the API response structure is invalid", () => {
      it("Then it should log validation issues for wrapped responses", async () => {
        const errorSpy = vi
          .spyOn(console, "error")
          .mockImplementation(() => undefined);
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: { id: "1" },
              }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "Invalid data from API",
        );
        expect(errorSpy).toHaveBeenCalledWith(
          "Data validation failed:",
          expect.anything(),
        );
        errorSpy.mockRestore();
        vi.unstubAllGlobals();
      });

      /**
       * Without a ``success`` field apiCall validates the raw JSON against the
       * schema directly; ``{data: {id, name}}`` fails it.
       */
      it("Then it should throw an ApiError for missing success field", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ data: { id: "1", name: "Test" } }),
          }),
        );
        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "Invalid data from API",
        );
        vi.unstubAllGlobals();
      });

      it("Then it should throw an ApiError for invalid data structure", async () => {
        const errorSpy = vi
          .spyOn(console, "error")
          .mockImplementation(() => undefined);
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () =>
              Promise.resolve({
                success: true,
                data: { id: "1" },
              }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "Invalid data from API",
        );
        expect(errorSpy).toHaveBeenCalledWith(
          "Data validation failed:",
          expect.anything(),
        );
        errorSpy.mockRestore();
        vi.unstubAllGlobals();
      });

      it("Then it should log validation issues for direct responses", async () => {
        const errorSpy = vi
          .spyOn(console, "error")
          .mockImplementation(() => undefined);
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () => Promise.resolve({ id: "1" }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "Invalid data from API",
        );
        expect(errorSpy).toHaveBeenCalledWith(
          "Data validation failed:",
          expect.anything(),
        );
        errorSpy.mockRestore();
        vi.unstubAllGlobals();
      });
    });

    describe("When the API returns a success=false response", () => {
      it("Then it should throw an ApiError with the error message", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () =>
              Promise.resolve({
                success: false,
                error: {
                  code: "VALIDATION_FAILED",
                  message: "Invalid input data",
                },
              }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "Invalid input data",
        );
        vi.unstubAllGlobals();
      });

      it("Then the error code should be included in the ApiError", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () =>
              Promise.resolve({
                success: false,
                error: {
                  code: "AUTH_REQUIRED",
                  message: "Authentication required",
                },
              }),
          }),
        );

        try {
          await apiCall("/api/test", testSchema);
        } catch (error) {
          expect(error).toBeInstanceOf(ApiError);
          expect((error as ApiError).code).toBe("AUTH_REQUIRED");
        }
        vi.unstubAllGlobals();
      });

      it("Then it should handle malformed error responses", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: true,
            json: () =>
              Promise.resolve({
                success: false,
              }),
          }),
        );

        await expect(apiCall("/api/test", testSchema)).rejects.toThrow(
          "API request failed",
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

      it("Then it should reject non-boolean success values", () => {
        const invalid = {
          success: "yes",
          data: { id: "1" },
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

      it("Then it should require error code and message fields", () => {
        const invalid = {
          success: false,
          error: { code: "ONLY_CODE" },
        };
        expect(errorResponseSchema.safeParse(invalid).success).toBe(false);
      });
    });
  });

  describe("Given the apiCallNoContent function", () => {
    afterEach(() => {
      vi.unstubAllGlobals();
    });

    describe("When called without custom options", () => {
      it("Then it should include credentials and default headers", async () => {
        const mockFetch = vi.fn().mockResolvedValue({
          ok: true,
          status: 204,
        });
        vi.stubGlobal("fetch", mockFetch);

        await apiCallNoContent("/api/documents/1");

        expect(mockFetch).toHaveBeenCalledWith(
          "/api/documents/1",
          expect.objectContaining({
            credentials: "include",
            headers: expect.objectContaining({
              "Content-Type": "application/json",
            }) as unknown,
          }),
        );
      });

      it("Then it should resolve without a value on success", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({ ok: true, status: 204 }),
        );

        await expect(
          apiCallNoContent("/api/documents/1"),
        ).resolves.toBeUndefined();
      });
    });

    describe("When the API returns 401 Unauthorized", () => {
      it("Then it should redirect to login and throw ApiError", async () => {
        const location = mockWindowLocation();
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
            json: () =>
              Promise.resolve({
                message: "Session expired",
                code: "AUTH_EXPIRED",
              }),
          }),
        );

        await expect(
          apiCallNoContent("/api/conversations/1", { method: "DELETE" }),
        ).rejects.toMatchObject({
          status: 401,
          message: "Session expired",
          code: "AUTH_EXPIRED",
        });
        expect(location.href).toContain("/auth/logout");
        expect(location.href).not.toContain("/api/");
      });

      it("Then it should fall back to Unauthorized when the body is not JSON", async () => {
        const location = mockWindowLocation();
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 401,
            json: () => {
              return Promise.reject(new Error("not json"));
            },
          }),
        );

        await expect(
          apiCallNoContent("/api/conversations/1", { method: "DELETE" }),
        ).rejects.toMatchObject({
          status: 401,
          message: "Unauthorized",
        });
        expect(location.href).toContain("/auth/logout");
        expect(location.href).not.toContain("/api/");
      });
    });

    describe("When the API returns 204 No Content", () => {
      it("Then it should resolve without a value", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({ ok: true, status: 204 }),
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
        });
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
            }) as unknown,
          }),
        );
        vi.unstubAllGlobals();
      });
    });

    describe("When the API returns 403 Forbidden", () => {
      it("Then it should redirect to the forbidden page and throw ApiError", async () => {
        const location = mockWindowLocation();
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 403,
            json: () =>
              Promise.resolve({
                message: "Access denied",
                code: "ACL_DENY",
              }),
          }),
        );

        await expect(
          apiCallNoContent("/api/conversations/1", { method: "DELETE" }),
        ).rejects.toMatchObject({
          status: 403,
          message: "Access denied",
          code: "ACL_DENY",
        });
        expect(location.href).toBe("/403");
      });

      it("Then it should fall back to Forbidden when the body is not JSON", async () => {
        const location = mockWindowLocation();
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 403,
            json: () => {
              return Promise.reject(new Error("not json"));
            },
          }),
        );

        await expect(
          apiCallNoContent("/api/conversations/1", { method: "DELETE" }),
        ).rejects.toMatchObject({
          status: 403,
          message: "Forbidden",
        });
        expect(location.href).toBe("/403");
      });
    });

    describe("When the API returns a 4xx error", () => {
      it("Then it should throw an ApiError with the returned message", async () => {
        vi.stubGlobal(
          "fetch",
          vi.fn().mockResolvedValue({
            ok: false,
            status: 404,
            json: () => Promise.resolve({ message: "Document not found" }),
          }),
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
            json: () =>
              Promise.resolve({ message: "forbidden", code: "ACL_DENY" }),
          }),
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
            json: () => {
              return Promise.reject(new Error("not json"));
            },
          }),
        );

        await expect(
          apiCallNoContent("/api/documents/1", { method: "DELETE" }),
        ).rejects.toThrow("HTTP error! status: 500");
        vi.unstubAllGlobals();
      });
    });
  });

  describe("Given apiCall runs without a browser window", () => {
    const testSchema = z.object({ id: z.string() });
    let originalWindow: Window & typeof globalThis;

    beforeEach(() => {
      originalWindow = globalThis.window;
    });

    afterEach(() => {
      globalThis.window = originalWindow;
      vi.unstubAllGlobals();
    });

    it("Then apiCall should throw without redirecting on 401", async () => {
      const location = mockWindowLocation();
      // @ts-expect-error simulate SSR where window is unavailable
      delete globalThis.window;

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 401,
          json: () =>
            Promise.resolve({ message: "Session expired", code: "AUTH" }),
        }),
      );

      await expect(apiCall("/api/test", testSchema)).rejects.toMatchObject({
        status: 401,
        message: "Session expired",
        code: "AUTH",
      });
      expect(location.href).toBe("");
    });

    it("Then apiCall should throw without redirecting on 403", async () => {
      const location = mockWindowLocation();
      // @ts-expect-error simulate SSR where window is unavailable
      delete globalThis.window;

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 403,
          json: () => Promise.resolve({ message: "Access denied" }),
        }),
      );

      await expect(apiCall("/api/test", testSchema)).rejects.toMatchObject({
        status: 403,
        message: "Access denied",
      });
      expect(location.href).toBe("");
    });

    it("Then apiCallNoContent should throw without redirecting on 401", async () => {
      const location = mockWindowLocation();
      // @ts-expect-error simulate SSR where window is unavailable
      delete globalThis.window;

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 401,
          json: () => Promise.resolve({ message: "Session expired" }),
        }),
      );

      await expect(apiCallNoContent("/api/documents/1")).rejects.toMatchObject({
        status: 401,
        message: "Session expired",
      });
      expect(location.href).toBe("");
    });

    it("Then apiCallNoContent should throw without redirecting on 403", async () => {
      const location = mockWindowLocation();
      // @ts-expect-error simulate SSR where window is unavailable
      delete globalThis.window;

      vi.stubGlobal(
        "fetch",
        vi.fn().mockResolvedValue({
          ok: false,
          status: 403,
          json: () =>
            Promise.resolve({ message: "Access denied", code: "ACL_DENY" }),
        }),
      );

      await expect(apiCallNoContent("/api/documents/1")).rejects.toMatchObject({
        status: 403,
        message: "Access denied",
        code: "ACL_DENY",
      });
      expect(location.href).toBe("");
    });
  });
});

describe("API Client error details and redirects", () => {
  const detailSchema = z.object({ id: z.string() });
  const DETAIL = [{ msg: "field required" }];

  afterEach(() => {
    vi.unstubAllGlobals();
  });

  function stubErrorResponse(status: number, body: Record<string, unknown>) {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status,
        json: () => Promise.resolve(body),
      }),
    );
  }

  async function catchApiError(): Promise<ApiError> {
    const error = await apiCall("/api/test", detailSchema).catch(
      (caught: unknown) => caught,
    );
    expect(error).toBeInstanceOf(ApiError);
    return error as ApiError;
  }

  // Scenario: Only a 403 sends the browser to the forbidden page
  it.each([404, 422, 500])(
    "does not redirect the browser to the forbidden page on a %i",
    async (status) => {
      const location = mockWindowLocation();
      stubErrorResponse(status, { message: "failed" });

      await catchApiError();

      expect(location.href).toBe("");
    },
  );

  // Scenario: A validation error keeps the raw detail
  it("keeps the raw detail of a non-auth error", async () => {
    stubErrorResponse(422, { message: "invalid", detail: DETAIL });

    const error = await catchApiError();

    expect(error.detail).toEqual(DETAIL);
  });

  // Scenario: Auth errors do not expose the raw detail
  it.each([401, 403])("drops the raw detail of a %i error", async (status) => {
    mockWindowLocation();
    stubErrorResponse(status, { message: "denied", detail: DETAIL });

    const error = await catchApiError();

    expect(error.detail).toBeUndefined();
  });
});
