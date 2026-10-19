"use client";

/**
 * Unsaved-changes guard of the blog editor (AE-0424, F-12).
 *
 * While the draft differs from the saved post: closing/reloading the tab
 * triggers the browser's `beforeunload` prompt, and an in-app link click asks
 * for confirmation first (App Router navigations do not fire `beforeunload`).
 * `confirmLeave()` lets the editor's own "Back" button ask the same question.
 */

import { useEffect } from "react";

const LINK_SELECTOR = "a[href]";
const NEW_TAB_TARGET = "_blank";

function linkOf(event: MouseEvent): Element | null {
  const target = event.target;
  return target instanceof Element ? target.closest(LINK_SELECTOR) : null;
}

export function useUnsavedChangesGuard(
  dirty: boolean,
  message: string,
): { confirmLeave: () => boolean } {
  useEffect(() => {
    if (!dirty) {
      return undefined;
    }
    const onBeforeUnload = (event: BeforeUnloadEvent): void => {
      event.preventDefault();
    };
    const onLinkClick = (event: MouseEvent): void => {
      const link = linkOf(event);
      if (!link || link.getAttribute("target") === NEW_TAB_TARGET) {
        return;
      }
      if (!window.confirm(message)) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    document.addEventListener("click", onLinkClick, true);
    return () => {
      window.removeEventListener("beforeunload", onBeforeUnload);
      document.removeEventListener("click", onLinkClick, true);
    };
  }, [dirty, message]);

  return { confirmLeave: () => !dirty || window.confirm(message) };
}
