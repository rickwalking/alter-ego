"use client";

import { useEffect, useLayoutEffect, useRef } from "react";
import type { RefObject } from "react";

/** How close to the bottom (px) still counts as "reading the latest". */
export const STICK_TO_BOTTOM_THRESHOLD_PX = 80;

export interface StickToBottomKeys {
  /** Changes whenever the content grows (a new message or streamed text). */
  contentKey: string;
  /** True while a turn is in flight; each send scrolls the user's message into view. */
  sending: boolean;
}

function isNearBottom(element: HTMLElement): boolean {
  const distance =
    element.scrollHeight - element.scrollTop - element.clientHeight;
  return distance <= STICK_TO_BOTTOM_THRESHOLD_PX;
}

/**
 * Keep a scroll container pinned to its bottom while content streams in,
 * unless the reader scrolled up: then their position is left alone until they
 * scroll back down or send a message.
 */
export function useStickToBottom<T extends HTMLElement>({
  contentKey,
  sending,
}: StickToBottomKeys): RefObject<T | null> {
  const containerRef = useRef<T | null>(null);
  const pinnedRef = useRef(true);

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const onScroll = (): void => {
      pinnedRef.current = isNearBottom(element);
    };
    element.addEventListener("scroll", onScroll, { passive: true });
    return () => element.removeEventListener("scroll", onScroll);
  }, []);

  useLayoutEffect(() => {
    if (sending) pinnedRef.current = true;
  }, [sending]);

  useLayoutEffect(() => {
    const element = containerRef.current;
    if (!element || !pinnedRef.current) return;
    element.scrollTop = element.scrollHeight;
  }, [contentKey, sending]);

  return containerRef;
}
