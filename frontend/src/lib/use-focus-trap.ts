/**
 * AE-0273: trap keyboard focus inside a container while `active`. On activate,
 * focus moves to the first focusable element; Tab/Shift+Tab cycle within the
 * container; on deactivate, focus returns to whatever was focused before
 * (the drawer trigger). Reusable by the sidebar (AE-0273) and chat (AE-0276)
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

export function useFocusTrap(
  ref: RefObject<HTMLElement | null>,
  active: boolean,
): void {
  useEffect(() => {
    if (!active) {
      return;
    }
    const node = ref.current;
    if (!node) {
      return;
    }
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusable = (): HTMLElement[] =>
      Array.from(node.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR));

    focusable()[0]?.focus();

    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key !== TAB_KEY) {
        return;
      }
      const items = focusable();
      if (items.length === 0) {
        return;
      }
      const first = items[0];
      const last = items[items.length - 1];
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

    node.addEventListener("keydown", handleKeyDown);
    return () => {
      node.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus();
    };
  }, [ref, active]);
}
