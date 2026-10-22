"use client";

import { useEffect, useRef, useState } from "react";
import type { LeaveGuard } from "./types";

const LINK_SELECTOR = "a[href]";
const NEW_TAB_TARGET = "_blank";
const PRIMARY_BUTTON = 0;

function isPlainClick(event: MouseEvent): boolean {
  return (
    event.button === PRIMARY_BUTTON &&
    !event.metaKey &&
    !event.ctrlKey &&
    !event.shiftKey &&
    !event.altKey
  );
}

function isSameTabLink(link: Element | null): link is HTMLAnchorElement {
  return (
    link instanceof HTMLAnchorElement &&
    link.target !== NEW_TAB_TARGET &&
    link.origin === window.location.origin
  );
}

function guardedLink(event: MouseEvent): HTMLAnchorElement | null {
  if (!isPlainClick(event) || !(event.target instanceof Element)) {
    return null;
  }
  const link = event.target.closest(LINK_SELECTOR);
  return isSameTabLink(link) ? link : null;
}

/**
 * Asks before leaving the page while ``dirty``. An in-app link click is held
 * and ``asking`` turns on so the page shows its own dialog; ``leave`` replays
 * the click (the router then navigates), ``stay`` drops it. Closing or
 * reloading the tab keeps the browser's own ``beforeunload`` prompt, the only
 * one a page may show there.
 */
export function useLeaveGuard(dirty: boolean): LeaveGuard {
  const [held, setHeld] = useState<HTMLAnchorElement | null>(null);
  const replaying = useRef(false);
  const leaving = useRef(false);

  useEffect(() => {
    if (!dirty) {
      return undefined;
    }
    const onBeforeUnload = (event: BeforeUnloadEvent): void => {
      if (leaving.current) {
        return;
      }
      event.preventDefault();
    };
    const onLinkClick = (event: MouseEvent): void => {
      if (replaying.current) {
        replaying.current = false;
        return;
      }
      const link = guardedLink(event);
      if (!link) {
        return;
      }
      event.preventDefault();
      event.stopPropagation();
      setHeld(link);
    };
    const listeners = new AbortController();
    const { signal } = listeners;
    window.addEventListener("beforeunload", onBeforeUnload, { signal });
    document.addEventListener("click", onLinkClick, { capture: true, signal });
    return () => listeners.abort();
  }, [dirty]);

  return {
    asking: held !== null,
    stay: () => setHeld(null),
    leave: () => {
      const link = held;
      setHeld(null);
      if (link) {
        leaving.current = true;
        replaying.current = true;
        link.click();
      }
      return Promise.resolve();
    },
  };
}
