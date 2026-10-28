"use client";

import { useCallback, useEffect, type RefObject } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import {
  type BoardFilters,
  boardFiltersHref,
  parseBoardFilters,
} from "@/app/dashboard/workflow/board-filters";

/**
 * Owns the board toolbar state in the URL (`?q=&status=&sort=`), so a reload,
 * a shared link, or Back from a carousel restores the same view. Updates
 * replace the history entry (typing in the search box must not spam Back).
 */
export function useBoardFilters(): {
  filters: BoardFilters;
  setFilters: (next: BoardFilters) => void;
} {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const filters = parseBoardFilters(searchParams);
  const setFilters = useCallback(
    (next: BoardFilters): void => {
      router.replace(boardFiltersHref(pathname, next), { scroll: false });
    },
    [router, pathname],
  );
  return { filters, setFilters };
}

const SEARCH_SHORTCUT_KEY = "/";
const EDITABLE_TAGS: ReadonlySet<string> = new Set([
  "INPUT",
  "TEXTAREA",
  "SELECT",
]);

function isEditableTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false;
  return EDITABLE_TAGS.has(target.tagName) || target.isContentEditable;
}

/**
 * `/` focuses the board search box from anywhere on the page, unless the
 * owner is typing in an editable field.
 */
export function useSearchShortcut(
  inputRef: RefObject<HTMLInputElement | null>,
): void {
  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent): void => {
      if (event.defaultPrevented || event.key !== SEARCH_SHORTCUT_KEY) return;
      if (isEditableTarget(event.target)) return;
      event.preventDefault();
      inputRef.current?.focus();
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [inputRef]);
}
