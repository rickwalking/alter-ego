"use client";

/**
 * Storage access that never throws: a disabled or full storage (private-mode
 * quota errors) must not break the board or block card navigation, so reads
 * return null and writes are dropped silently.
 */

export function safeStorageGet(
  storage: Pick<Storage, "getItem">,
  key: string,
): string | null {
  try {
    return storage.getItem(key);
  } catch {
    return null;
  }
}

export function safeStorageSet(
  storage: Pick<Storage, "setItem">,
  key: string,
  value: string,
): void {
  try {
    storage.setItem(key, value);
  } catch {
    return;
  }
}

export function safeStorageRemove(
  storage: Pick<Storage, "removeItem">,
  key: string,
): void {
  try {
    storage.removeItem(key);
  } catch {
    return;
  }
}
