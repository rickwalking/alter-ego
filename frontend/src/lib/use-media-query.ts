/**
 * AE-0273/AE-0276: subscribe to a CSS media query via useSyncExternalStore (the
 * canonical external-store subscription — no setState-in-effect). Returns false
 * during SSR and when matchMedia is absent/partial (jsdom), so drawer scroll-lock
 * and focus-trap never engage on desktop. Used to gate drawer behavior to below
 * its breakpoint.
 */
import { useCallback, useSyncExternalStore } from "react";

function hasMatchMedia(): boolean {
  return (
    typeof window !== "undefined" && typeof window.matchMedia === "function"
  );
}

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void): (() => void) => {
      if (!hasMatchMedia()) {
        return () => {};
      }
      const mql = window.matchMedia(query);
      // jsdom / partial mocks can return undefined or omit the listener API.
      if (!mql || typeof mql.addEventListener !== "function") {
        return () => {};
      }
      mql.addEventListener("change", onChange);
      return () => mql.removeEventListener("change", onChange);
    },
    [query],
  );

  const getSnapshot = useCallback((): boolean => {
    if (!hasMatchMedia()) {
      return false;
    }
    const mql = window.matchMedia(query);
    return mql ? mql.matches : false;
  }, [query]);

  // SSR snapshot is always false (no viewport on the server).
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
