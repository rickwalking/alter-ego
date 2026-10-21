/**
 * Lock body scroll while an off-canvas surface (drawer/modal) is open.
 * Restores the prior inline values on cleanup. `overscroll-behavior: contain`
 * stops the scroll chain from leaking to the page behind the drawer.
 *
 * Reusable primitive — the dashboard sidebar and the chat drawer
 * both consume it, so the behavior is defined once (no jscpd dup).
 */
import { useEffect } from "react";

const LOCKED_OVERFLOW = "hidden";
const LOCKED_OVERSCROLL = "contain";

let lockCount = 0;
let savedOverflow = "";
let savedOverscroll = "";

/**
 * Reference-counted, so concurrent locks (the sidebar drawer and the chat
 * drawer) never corrupt each other's saved body styles: the original is
 * captured on the first lock and restored when the last one releases.
 */
export function useScrollLock(active: boolean): void {
  useEffect(() => {
    if (!active) {
      return;
    }
    const body = document.body;
    if (lockCount === 0) {
      savedOverflow = body.style.overflow;
      savedOverscroll = body.style.overscrollBehavior;
      body.style.overflow = LOCKED_OVERFLOW;
      body.style.overscrollBehavior = LOCKED_OVERSCROLL;
    }
    lockCount += 1;
    return () => {
      lockCount -= 1;
      if (lockCount === 0) {
        body.style.overflow = savedOverflow;
        body.style.overscrollBehavior = savedOverscroll;
      }
    };
  }, [active]);
}
