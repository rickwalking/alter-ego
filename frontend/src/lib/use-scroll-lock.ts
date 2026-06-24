/**
 * AE-0273: lock body scroll while an off-canvas surface (drawer/modal) is open.
 * Restores the prior inline values on cleanup. `overscroll-behavior: contain`
 * stops the scroll chain from leaking to the page behind the drawer.
 *
 * Reusable primitive — the dashboard sidebar (AE-0273) and the chat drawer
 * (AE-0276) both consume it, so the behavior is defined once (no jscpd dup).
 */
import { useEffect } from "react";

const LOCKED_OVERFLOW = "hidden";
const LOCKED_OVERSCROLL = "contain";

export function useScrollLock(active: boolean): void {
  useEffect(() => {
    if (!active) {
      return;
    }
    const body = document.body;
    const previousOverflow = body.style.overflow;
    const previousOverscroll = body.style.overscrollBehavior;
    body.style.overflow = LOCKED_OVERFLOW;
    body.style.overscrollBehavior = LOCKED_OVERSCROLL;
    return () => {
      body.style.overflow = previousOverflow;
      body.style.overscrollBehavior = previousOverscroll;
    };
  }, [active]);
}
