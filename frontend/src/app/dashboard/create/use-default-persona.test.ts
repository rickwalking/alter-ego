import { describe, expect, it, vi } from "vitest";
import { renderHook } from "@testing-library/react";
import { defaultPersonaId, useDefaultPersona } from "./use-default-persona";

// Gherkin: tests/features/create-content-mode.feature (AE-0373)
describe("defaultPersonaId", () => {
  it("finds Pedro case-insensitively", () => {
    expect(
      defaultPersonaId([
        { id: "a", name: "Other" },
        { id: "b", name: " pedro " },
      ]),
    ).toBe("b");
  });

  it("returns empty when there is no Pedro", () => {
    expect(defaultPersonaId([{ id: "a", name: "Other" }])).toBe("");
  });
});

describe("useDefaultPersona", () => {
  it("selects Pedro once the list loads", () => {
    const onSelect = vi.fn();
    const { rerender } = renderHook(
      ({ personas }) => useDefaultPersona(personas, onSelect),
      { initialProps: { personas: [] as { id: string; name: string }[] } },
    );
    expect(onSelect).not.toHaveBeenCalled();
    rerender({ personas: [{ id: "p", name: "Pedro" }] });
    expect(onSelect).toHaveBeenCalledWith("p");
    rerender({
      personas: [
        { id: "p", name: "Pedro" },
        { id: "q", name: "X" },
      ],
    });
    expect(onSelect).toHaveBeenCalledTimes(1);
  });

  it("selects nothing without a Pedro persona", () => {
    const onSelect = vi.fn();
    renderHook(() => useDefaultPersona([{ id: "x", name: "X" }], onSelect));
    expect(onSelect).not.toHaveBeenCalled();
  });
});
