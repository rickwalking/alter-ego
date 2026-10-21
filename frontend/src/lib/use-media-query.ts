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

/**
 * jsdom / partial test mocks can return undefined or omit the listener API, so
 * the list is typed as partial instead of trusting the DOM lib's signature.
 */
function mediaQueryList(query: string): Partial<MediaQueryList> | undefined {
  return window.matchMedia(query);
}

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void): (() => void) => {
      if (!hasMatchMedia()) {
        return () => undefined;
      }
      const mql = mediaQueryList(query);
      if (!mql?.addEventListener || !mql.removeEventListener) {
        return () => undefined;
      }
      const { addEventListener, removeEventListener } = mql;
      addEventListener.call(mql, "change", onChange);
      return () => removeEventListener.call(mql, "change", onChange);
    },
    [query],
  );

  const getSnapshot = useCallback((): boolean => {
    if (!hasMatchMedia()) {
      return false;
    }
    return mediaQueryList(query)?.matches ?? false;
  }, [query]);

  // SSR snapshot is always false (no viewport on the server).
  return useSyncExternalStore(subscribe, getSnapshot, () => false);
}
