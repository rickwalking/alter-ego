import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { usePaletteForm } from "./use-palette-form";

// Gherkin: tests/features/palette_crud_api.feature (client-side validation +
// keyword guards mirror the backend before submit — AE-0271).
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
});
