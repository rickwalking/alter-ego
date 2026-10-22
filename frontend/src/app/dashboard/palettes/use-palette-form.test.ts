import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { usePaletteForm } from "./use-palette-form";

describe("usePaletteForm", () => {
  it("is invalid until a name and valid hex colours are present", () => {
    const { result } = renderHook(() => usePaletteForm());
    act(() => result.current.setField("name", ""));
    expect(result.current.isValid).toBe(false);
    act(() => result.current.setField("name", "Aurora"));
    expect(result.current.isValid).toBe(true);
  });

  it("flags a non-hex colour", () => {
    const { result } = renderHook(() => usePaletteForm());
    act(() => result.current.setField("primary", "red; ignore"));
    expect(result.current.errors.primary).toBeDefined();
    expect(result.current.isValid).toBe(false);
  });

  it("rejects a name with angle brackets (XSS guard, mirrors backend)", () => {
    const { result } = renderHook(() => usePaletteForm());
    act(() => result.current.setField("name", "<script>x</script>"));
    expect(result.current.errors.name).toBeDefined();
    expect(result.current.isValid).toBe(false);
  });

  it("dedupes and lowercases keywords", () => {
    const { result } = renderHook(() => usePaletteForm());
    act(() => result.current.addKeywords("Space, space, NEON"));
    expect(result.current.state.keywords).toEqual(["space", "neon"]);
  });

  it("caps keywords at ten", () => {
    const { result } = renderHook(() => usePaletteForm());
    const many = Array.from({ length: 15 }, (_, i) => `kw${i}`).join(",");
    act(() => result.current.addKeywords(many));
    expect(result.current.state.keywords).toHaveLength(10);
  });

  it("removes a keyword", () => {
    const { result } = renderHook(() => usePaletteForm());
    act(() => result.current.addKeywords("a,b"));
    act(() => result.current.removeKeyword("a"));
    expect(result.current.state.keywords).toEqual(["b"]);
  });

  it("builds a request from the trimmed name", () => {
    const { result } = renderHook(() => usePaletteForm());
    act(() => result.current.setField("name", "  Aurora  "));
    expect(result.current.toRequest().name).toBe("Aurora");
  });

  /** Scenario: Using a candidate pre-fills the form without saving */
  it("replaces every field with a candidate and caps its keywords", () => {
    const { result } = renderHook(() => usePaletteForm());
    act(() =>
      result.current.applyCandidate({
        name: "Areia",
        primary: "#1d4ed8",
        accent: "#9a3412",
        background: "#f8f5ee",
        mode: "light",
        keywords: Array.from({ length: 12 }, (_, i) => `k${i}`),
        contrast: { text: 16.2, primary: 6.1, accent: 6.9 },
      }),
    );
    expect(result.current.state).toEqual({
      name: "Areia",
      primary: "#1d4ed8",
      accent: "#9a3412",
      background: "#f8f5ee",
      mode: "light",
      keywords: Array.from({ length: 10 }, (_, i) => `k${i}`),
    });
    expect(result.current.isValid).toBe(true);
  });
});
