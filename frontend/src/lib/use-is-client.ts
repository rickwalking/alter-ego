import { useSyncExternalStore } from "react";

function subscribeNever(): () => void {
  return () => undefined;
}

function onClient(): boolean {
  return true;
}

function onServer(): boolean {
  return false;
}

/**
 * False during the server render and hydration, true afterwards in the browser.
 * Lets a subtree that can only load in the browser (e.g. an authenticated
 * client API call) render its fallback on the server instead of failing there.
 */
export function useIsClient(): boolean {
  return useSyncExternalStore(subscribeNever, onClient, onServer);
}
