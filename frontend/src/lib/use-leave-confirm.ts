"use client";

/**
 * The in-app "leave without saving?" step of a create/edit form. Leaving a
 * form without changes happens at once; with changes it opens a confirmation
 * dialog first. Escape asks to leave while that dialog is closed (the dialog
 * closes itself on Escape), when focus is inside the form or on the page
 * body, so Escape in another surface (the mobile menu drawer) only closes it.
 */
import { useEffect, useState, type RefObject } from "react";

const ESCAPE_KEY = "Escape";

export interface LeaveConfirm {
  /** True while the confirmation dialog is shown. */
  open: boolean;
  /** Leave now, or ask first when there are unsaved changes. */
  request: () => void;
  /** Leave without saving (the dialog's confirm action). */
  confirm: () => Promise<void>;
  /** Close the dialog and keep editing. */
  stay: () => void;
}

/** True when a key press belongs to the form: focus inside it or on the body. */
function isInScope(
  target: EventTarget | null,
  scope: HTMLElement | null,
): boolean {
  if (!(target instanceof Node) || target === document.body) {
    return true;
  }
  return scope?.contains(target) ?? false;
}

function useEscapeToLeave(
  scopeRef: RefObject<HTMLElement | null>,
  active: boolean,
  request: () => void,
): void {
  useEffect(() => {
    if (!active) {
      return;
    }
    const onKeyDown = (event: KeyboardEvent): void => {
      if (
        event.key === ESCAPE_KEY &&
        isInScope(event.target, scopeRef.current)
      ) {
        request();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [scopeRef, active, request]);
}

export function useLeaveConfirm(
  scopeRef: RefObject<HTMLElement | null>,
  dirty: boolean,
  onLeave: () => void,
): LeaveConfirm {
  const [open, setOpen] = useState(false);
  const request = (): void => {
    if (!dirty) {
      onLeave();
      return;
    }
    setOpen(true);
  };
  useEscapeToLeave(scopeRef, !open, request);
  return {
    open,
    request,
    confirm: () => {
      setOpen(false);
      onLeave();
      return Promise.resolve();
    },
    stay: () => setOpen(false),
  };
}
