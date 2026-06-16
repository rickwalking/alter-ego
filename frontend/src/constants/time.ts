/** Canonical time-unit constants for duration math (avoids magic numbers). */

export const MS_PER_SECOND = 1000;
export const SECONDS_PER_MINUTE = 60;
export const MINUTES_PER_HOUR = 60;
export const HOURS_PER_DAY = 24;
export const DAYS_PER_WEEK = 7;

export const SECONDS_PER_HOUR = SECONDS_PER_MINUTE * MINUTES_PER_HOUR;
export const SECONDS_PER_DAY = SECONDS_PER_HOUR * HOURS_PER_DAY;
export const SECONDS_PER_WEEK = SECONDS_PER_DAY * DAYS_PER_WEEK;

export const MS_PER_MINUTE = MS_PER_SECOND * SECONDS_PER_MINUTE;
