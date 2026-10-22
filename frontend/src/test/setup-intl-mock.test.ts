/**
 * The global next-intl mock in setup.ts must keep the translator identity
 * stable, as next-intl does.
 */
import { renderHook } from "@testing-library/react";
import { useEffect } from "react";
import { useTranslations } from "next-intl";
import { describe, expect, it, vi } from "vitest";

describe("global next-intl test mock", () => {
  it("returns the same translator across renders", () => {
    // Scenario: The translator keeps its identity across renders
    const { result, rerender } = renderHook(() => useTranslations("common"));
    const first = result.current;
    rerender();
    expect(result.current).toBe(first);
  });

  it("keeps namespaces apart and translates through en.json", () => {
    // Scenario: The translator keeps its identity across renders
    const { result } = renderHook(() => ({
      common: useTranslations("common"),
      other: useTranslations("workflow.errors"),
    }));
    expect(result.current.common).not.toBe(result.current.other);
    expect(result.current.other("unknown")).not.toBe("");
  });

  it("does not re-run an effect keyed on the translator", () => {
    // Scenario: An effect keyed on the translator runs once
    const effect = vi.fn();
    const { rerender } = renderHook(() => {
      const t = useTranslations("common");
      useEffect(() => {
        effect(t);
      }, [t]);
    });
    rerender();
    rerender();
    expect(effect).toHaveBeenCalledTimes(1);
  });
});
