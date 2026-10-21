import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import { DEFAULT_LOCALE } from "@/i18n/config";
import { formatLocaleDate } from "@/lib/locale-format";

import {
  MS_PER_SECOND,
  SECONDS_PER_MINUTE,
  SECONDS_PER_HOUR,
  SECONDS_PER_DAY,
  SECONDS_PER_WEEK,
} from "@/constants/time";

/** Characters of the "..." ellipsis appended by `truncate`. */
const ELLIPSIS_LENGTH = 3;

/** Radix for base-36 random-suffix generation in the `generateId` fallback. */
const BASE36_RADIX = 36;
/** Slice bounds for the base-36 fractional suffix ("0." prefix dropped). */
const BASE36_SUFFIX_START = 2;
const BASE36_SUFFIX_END = 9;

/** Number of distinct 32-bit unsigned values (2^32). */
const UINT32_RANGE = 4_294_967_296;

/**
 * Merge Tailwind CSS classes with proper precedence
 * Combines clsx for conditional classes and tailwind-merge for deduplication
 */
export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/**
 * Format a date to a readable string in `locale` (en by default:
 * "Jan 15, 2024", pt "15/01/2024").
 */
export function formatDate(
  date: Date | string | number,
  locale: string = DEFAULT_LOCALE,
): string {
  return formatLocaleDate(date, locale);
}

/**
 * Format a date to relative time (e.g., "2 hours ago")
 */
export function formatRelativeTime(date: Date | string | number): string {
  const now = new Date();
  const then = new Date(date);
  const seconds = Math.floor((now.getTime() - then.getTime()) / MS_PER_SECOND);

  if (seconds < SECONDS_PER_MINUTE) return "just now";
  if (seconds < SECONDS_PER_HOUR)
    return `${Math.floor(seconds / SECONDS_PER_MINUTE)}m ago`;
  if (seconds < SECONDS_PER_DAY)
    return `${Math.floor(seconds / SECONDS_PER_HOUR)}h ago`;
  if (seconds < SECONDS_PER_WEEK)
    return `${Math.floor(seconds / SECONDS_PER_DAY)}d ago`;

  return formatDate(date);
}

/**
 * Truncate a string to a maximum length
 */
export function truncate(str: string, maxLength: number): string {
  if (str.length <= maxLength) return str;
  return str.slice(0, maxLength - ELLIPSIS_LENGTH) + "...";
}

/**
 * First candidate with visible text, trimmed, or "" when none.
 * Use instead of chained `||` when an empty/blank string must not be displayed.
 */
export function firstNonBlank(
  candidates: readonly (string | null | undefined)[],
): string {
  for (const candidate of candidates) {
    const trimmed = candidate?.trim() ?? "";
    if (trimmed.length > 0) {
      return trimmed;
    }
  }
  return "";
}

/**
 * Generate a unique ID
 */
/** A uniform float in [0, 1) drawn from the Web Crypto CSPRNG. */
export function secureRandomUnit(): number {
  const [value = 0] = globalThis.crypto.getRandomValues(new Uint32Array(1));
  return value / UINT32_RANGE;
}

/** A unique id: ``crypto.randomUUID`` when available, else a time + random fallback. */
export function generateId(): string {
  const webCrypto = globalThis.crypto as Crypto | undefined;
  if (webCrypto?.randomUUID) {
    return webCrypto.randomUUID();
  }
  return `${Date.now()}-${secureRandomUnit()
    .toString(BASE36_RADIX)
    .substring(BASE36_SUFFIX_START, BASE36_SUFFIX_END)}`;
}

/**
 * Debounce a function
 */
export function debounce<T extends (...args: unknown[]) => unknown>(
  fn: T,
  delay: number,
): (...args: Parameters<T>) => void {
  let timeoutId: ReturnType<typeof setTimeout>;

  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => fn(...args), delay);
  };
}

/**
 * Throttle a function
 */
export function throttle<T extends (...args: unknown[]) => unknown>(
  fn: T,
  limit: number,
): (...args: Parameters<T>) => void {
  let inThrottle = false;

  return (...args: Parameters<T>) => {
    if (!inThrottle) {
      fn(...args);
      inThrottle = true;
      setTimeout(() => (inThrottle = false), limit);
    }
  };
}
