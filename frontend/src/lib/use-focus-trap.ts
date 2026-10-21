/**
 * Trap keyboard focus inside a container while `active`. On activate,
 * focus moves to the first focusable element; Tab/Shift+Tab cycle within the
 * container; on deactivate, focus returns to whatever was focused before
 * (the drawer trigger). Reusable by the sidebar and chat
 * drawers — single source, no jscpd duplication.
 */
import { useEffect, type RefObject } from "react";

const FOCUSABLE_SELECTOR = [
  "a[href]",
  "button:not([disabled])",
  "input:not([disabled])",
  "select:not([disabled])",
  "textarea:not([disabled])",
  '[tabindex]:not([tabindex="-1"])',
].join(",");

const TAB_KEY = "Tab";

function focusableIn(node: HTMLElement): HTMLElement[] {
  return Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));
}

/** Tab / Shift+Tab wrap around the first and last focusable element. */
function trapTabKey(node: HTMLElement): (event: KeyboardEvent) => void {
  return (event: KeyboardEvent): void => {
    if (event.key !== TAB_KEY) {
      return;
    }
    const items = focusableIn(node);
    const first = items[0];
    const last = items[items.length - 1];
    if (first === undefined || last === undefined) {
      return;
    }
    const activeEl = document.activeElement;
    if (event.shiftKey && activeEl === first) {
      event.preventDefault();
      last.focus();
      return;
    }
    if (!event.shiftKey && activeEl === last) {
      event.preventDefault();
      first.focus();
    }
  };
}

export function useFocusTrap(
  ref: RefObject<HTMLElement | null>,
  active: boolean,
): void {
  useEffect(() => {
    const node = ref.current;
    if (!active || !node) {
      return;
    }
    const previouslyFocused = document.activeElement as HTMLElement | null;
    focusableIn(node)[0]?.focus();

    const handleKeyDown = trapTabKey(node);
    node.addEventListener("keydown", handleKeyDown);
    return () => {
      node.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [ref, active]);
}
