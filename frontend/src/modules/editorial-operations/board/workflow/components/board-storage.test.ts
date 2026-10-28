import { describe, expect, it } from "vitest";
import {
  safeStorageGet,
  safeStorageRemove,
  safeStorageSet,
} from "@/modules/editorial-operations/board/workflow/components/board-storage";

function throwingStorage(): Storage {
  const boom = (): never => {
    throw new Error("storage disabled");
  };
  return {
    getItem: boom,
    setItem: boom,
    removeItem: boom,
    clear: boom,
    key: boom,
    length: 0,
  };
}

describe("board storage safety", () => {
  it("returns null from a throwing read", () => {
    expect(safeStorageGet(throwingStorage(), "k")).toBeNull();
  });

  it("drops a write that exceeds the quota", () => {
    expect(() => safeStorageSet(throwingStorage(), "k", "v")).not.toThrow();
  });

  it("drops a removal that throws", () => {
    expect(() => safeStorageRemove(throwingStorage(), "k")).not.toThrow();
  });

  it("reads and writes through a working storage", () => {
    safeStorageSet(window.sessionStorage, "k", "v");
    expect(safeStorageGet(window.sessionStorage, "k")).toBe("v");
    safeStorageRemove(window.sessionStorage, "k");
    expect(safeStorageGet(window.sessionStorage, "k")).toBeNull();
  });
});
