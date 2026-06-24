/**
 * AE-0273: disclosure state for an off-canvas surface (drawer). Closes on
 * Escape and on route change (so navigating from inside the drawer dismisses
 * it). Reusable by the dashboard sidebar (AE-0273) and chat drawer (AE-0276) —
 * one source of truth, no jscpd duplication.
 */
import { useCallback, useEffect, useState } from "react";
import { usePathname } from "next/navigation";

const ESCAPE_KEY = "Escape";

export interface OffCanvasState {
  open: boolean;
  setOpen: (open: boolean) => void;
  toggle: () => void;
  close: () => void;
}

export function useOffCanvas(): OffCanvasState {
  const [open, setOpen] = useState(false);
  const pathname = usePathname();
  const [lastPathname, setLastPathname] = useState(pathname);

  const close = useCallback((): void => setOpen(false), []);
  const toggle = useCallback((): void => setOpen((value) => !value), []);

  // Close when the route changes (e.g. tapping a nav link inside the drawer).
  // Adjusting state during render on a changed value is the recommended pattern
  // over a setState-in-effect (avoids cascading renders).
  if (pathname !== lastPathname) {
    setLastPathname(pathname);
    setOpen(false);
  }

  // Close on Escape while open.
  useEffect(() => {
    if (!open) {
      return;
    }
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === ESCAPE_KEY) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [open]);

  return { open, setOpen, toggle, close };
}
