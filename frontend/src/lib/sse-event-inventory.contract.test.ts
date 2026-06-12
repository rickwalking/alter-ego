/**
 * Contract test freezing frontend SSE event-name constants (AE-0076).
 *
 * Feature: SSE event names are frozen during the migration
 * See tests/features/sse-event-inventory.feature
 *
 * Asserts that every value in EDITORIAL_WORKFLOW_SSE_EVENTS and SSE_EVENT_TYPE
 * equals the committed source-of-truth artifact
 * docs/architecture/sse-event-inventory.json. A constant-set comparison (not a
 * literal hunt): on drift the test fails naming the mismatched constant.
 */

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";
import { EDITORIAL_WORKFLOW_SSE_EVENTS } from "@/constants/editorial-workflow";
import { SSE_EVENT_TYPE } from "@/lib/sse-client";

interface FrontendModuleEntry {
  map: string;
  constants: Record<string, string>;
}

interface SseEventInventory {
  frontend: Record<string, FrontendModuleEntry>;
}

const CURRENT_DIR = dirname(fileURLToPath(import.meta.url));
// frontend/src/lib/<this file> -> up 3 = frontend/, up 4 = repo root.
const ARTIFACT_PATH = resolve(
  CURRENT_DIR,
  "../../../docs/architecture/sse-event-inventory.json",
);

const EDITORIAL_KEY = "src/constants/editorial-workflow.ts";
const CHAT_KEY = "src/lib/sse-client.ts";

function loadInventory(): SseEventInventory {
  return JSON.parse(readFileSync(ARTIFACT_PATH, "utf-8")) as SseEventInventory;
}

function diffConstants(
  label: string,
  actual: Record<string, string>,
  expected: Record<string, string>,
): string[] {
  const mismatches: string[] = [];
  for (const [key, value] of Object.entries(expected)) {
    if (actual[key] !== value) {
      mismatches.push(
        `${label}.${key}: inventory=${JSON.stringify(value)} actual=${JSON.stringify(actual[key])}`,
      );
    }
  }
  return mismatches;
}

describe("SSE event-name inventory contract", () => {
  const inventory = loadInventory();

  // Scenario: Frontend constants match the inventory
  //   Given the frontend EDITORIAL_WORKFLOW_SSE_EVENTS constants map
  //   When the frontend contract test compares its values to the inventory
  //   Then every frontend constant value exists in the inventory
  // Scenario: Drifted frontend constant is caught in CI
  //   Given a frontend event-name constant whose value differs
  //   Then the test fails and names the mismatched constant
  it("EDITORIAL_WORKFLOW_SSE_EVENTS matches the frozen inventory", () => {
    const expected = inventory.frontend[EDITORIAL_KEY].constants;
    const mismatches = diffConstants(
      "EDITORIAL_WORKFLOW_SSE_EVENTS",
      EDITORIAL_WORKFLOW_SSE_EVENTS,
      expected,
    );
    expect(
      mismatches,
      `SSE event-name drift (frozen until Phase 8). Update docs/architecture/sse-event-inventory.{json,md} and the backend constants in the same PR if intentional. Mismatches: ${mismatches.join("; ")}`,
    ).toEqual([]);
  });

  // Scenario: Frontend constants match the inventory (chat SSE_EVENT_TYPE map)
  // Scenario: Drifted frontend constant is caught in CI
  it("SSE_EVENT_TYPE matches the frozen inventory", () => {
    const expected = inventory.frontend[CHAT_KEY].constants;
    const mismatches = diffConstants("SSE_EVENT_TYPE", SSE_EVENT_TYPE, expected);
    expect(
      mismatches,
      `SSE event-name drift (frozen until Phase 8). Update docs/architecture/sse-event-inventory.{json,md} and the backend constants in the same PR if intentional. Mismatches: ${mismatches.join("; ")}`,
    ).toEqual([]);
  });

  it("inventory lists no frontend constant absent from the maps", () => {
    const liveMaps: Record<string, Readonly<Record<string, string>> | undefined> =
      {
        [EDITORIAL_KEY]: EDITORIAL_WORKFLOW_SSE_EVENTS,
        [CHAT_KEY]: SSE_EVENT_TYPE,
      };
    const missing: string[] = [];
    for (const [moduleKey, entry] of Object.entries(inventory.frontend)) {
      const live = liveMaps[moduleKey];
      for (const key of Object.keys(entry.constants)) {
        if (live === undefined || !(key in live)) {
          missing.push(`${entry.map}.${key}`);
        }
      }
    }
    expect(
      missing,
      `Inventory lists frontend constants not defined in the maps: ${missing.join(", ")}`,
    ).toEqual([]);
  });
});
