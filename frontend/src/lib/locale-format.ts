/**
 * Locale-aware date and number formatting for every surface (public
 * and dashboard). Components pass the active next-intl locale (`useLocale()`);
 * an unknown locale falls back to the default one. Invalid input prints "".
 */

import {
  DEFAULT_LOCALE,
  SUPPORTED_LOCALES,
  type SupportedLocale,
} from "@/i18n/config";
import {
  HOURS_PER_DAY,
  MINUTES_PER_HOUR,
  MS_PER_MINUTE,
} from "@/constants/time";

export type DateInput = Date | string | number | null | undefined;

const DATE_LOCALE_TAGS: Record<SupportedLocale, string> = {
  pt: "pt-BR",
  en: "en-US",
};
const DATE_FORMAT_BY_LOCALE: Record<
  SupportedLocale,
  Intl.DateTimeFormatOptions
> = {
  pt: { day: "2-digit", month: "2-digit", year: "numeric" },
  en: { month: "short", day: "numeric", year: "numeric" },
};
const CLOCK_FORMAT: Intl.DateTimeFormatOptions = {
  hour: "numeric",
  minute: "2-digit",
};
const RELATIVE_FORMAT: Intl.RelativeTimeFormatOptions = {
  style: "narrow",
  numeric: "auto",
};

export function toSupportedLocale(
  locale: string | null | undefined,
): SupportedLocale {
  const match = SUPPORTED_LOCALES.find((supported) => supported === locale);
  return match ?? DEFAULT_LOCALE;
}

/** BCP 47 tag for Intl (pt → pt-BR, en → en-US). */
export function toDateLocaleTag(locale: string | null | undefined): string {
  return DATE_LOCALE_TAGS[toSupportedLocale(locale)];
}

function toValidDate(value: DateInput): Date | null {
  if (value === null || value === undefined || value === "") {
    return null;
  }
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function formatWith(
  value: DateInput,
  locale: string,
  options: Intl.DateTimeFormatOptions,
): string {
  const date = toValidDate(value);
  if (!date) {
    return "";
  }
  return date.toLocaleString(toDateLocaleTag(locale), options);
}

/** Calendar date (pt: 17/10/2026, en: Oct 17, 2026). */
export function formatLocaleDate(
  value: DateInput,
  locale: string,
  timeZone?: string,
): string {
  const supported = toSupportedLocale(locale);
  return formatWith(value, supported, {
    ...DATE_FORMAT_BY_LOCALE[supported],
    timeZone,
  });
}

/** Date and clock time (pt: 17/10/2026, 14:05, en: Oct 17, 2026, 2:05 PM). */
export function formatLocaleDateTime(value: DateInput, locale: string): string {
  const supported = toSupportedLocale(locale);
  return formatWith(value, supported, {
    ...DATE_FORMAT_BY_LOCALE[supported],
    ...CLOCK_FORMAT,
  });
}

/** Clock time only (pt: 14:05, en: 2:05 PM). */
export function formatLocaleTime(value: DateInput, locale: string): string {
  return formatWith(value, locale, CLOCK_FORMAT);
}

/**
 * Relative time for the last day (pt: "agora", "há 5 min.", en: "now",
 * "5m ago"), the calendar date after that.
 */
export function formatLocaleRelative(
  value: DateInput,
  locale: string,
  nowMs: number = Date.now(),
): string {
  const date = toValidDate(value);
  if (!date) {
    return "";
  }
  const minutes = Math.floor((nowMs - date.getTime()) / MS_PER_MINUTE);
  const relative = new Intl.RelativeTimeFormat(
    toDateLocaleTag(locale),
    RELATIVE_FORMAT,
  );
  if (minutes < 1) {
    return relative.format(0, "second");
  }
  if (minutes < MINUTES_PER_HOUR) {
    return relative.format(-minutes, "minute");
  }
  const hours = Math.floor(minutes / MINUTES_PER_HOUR);
  if (hours < HOURS_PER_DAY) {
    return relative.format(-hours, "hour");
  }
  return formatLocaleDate(date, locale);
}

/** Integer with the locale's digit grouping (pt: 1.234, en: 1,234). */
export function formatLocaleNumber(value: number, locale: string): string {
  return value.toLocaleString(toDateLocaleTag(locale));
}
