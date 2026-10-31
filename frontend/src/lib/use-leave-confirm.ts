"use client";

/**
 * The in-app "leave without saving?" step of a create/edit form. Leaving a
 * form without changes happens at once; with changes it opens a confirmation
 * dialog first. Escape asks to leave while that dialog is closed (the dialog
 * closes itself on Escape).
 */
import { useState } from "react";
import { useCloseOnEscape } from "@/lib/use-off-canvas";

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

export function useLeaveConfirm(
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
  useCloseOnEscape(!open, request);
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
