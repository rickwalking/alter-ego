/**
 * Contract: the calendar's content-type mapping covers exactly the values the
 * backend publishes for `CalendarItemResponse.content_type` in the committed
 * OpenAPI artifact (docs/architecture/openapi.json).
 */
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { describe, expect, it } from "vitest";
import { CALENDAR_API_CONTENT_TYPES } from "./constants";

const OPENAPI_PATH = join(
  import.meta.dirname,
  "..",
  "..",
  "..",
  "..",
  "..",
  "..",
  "docs",
  "architecture",
  "openapi.json",
);

interface OpenApiDocument {
  components: {
    schemas: Record<
      string,
      { properties: Record<string, { enum?: string[] }> }
    >;
  };
}

describe("calendar content-type contract", () => {
  it("maps exactly the content types the API publishes", () => {
    // Scenario: The frontend mapping matches the published API values
    const openapi = JSON.parse(
      readFileSync(OPENAPI_PATH, "utf8"),
    ) as OpenApiDocument;
    const published =
      openapi.components.schemas.CalendarItemResponse?.properties.content_type
        ?.enum;

    expect(published).toBeDefined();
    const byName = (a: string, b: string): number => a.localeCompare(b);
    expect([...(published ?? [])].sort(byName)).toEqual(
      Object.keys(CALENDAR_API_CONTENT_TYPES).sort(byName),
    );
  });
});
