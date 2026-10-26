const QUEUE_TIME_ZONE = "America/Sao_Paulo";
const TIME_FORMAT: Intl.DateTimeFormatOptions = {
  hour: "2-digit",
  minute: "2-digit",
  hourCycle: "h23",
  timeZone: QUEUE_TIME_ZONE,
};
const DATE_FORMAT: Intl.DateTimeFormatOptions = {
  day: "2-digit",
  month: "2-digit",
  timeZone: QUEUE_TIME_ZONE,
};

export const QUEUE_ROW_CLASS =
  "flex flex-wrap items-center justify-between gap-2 rounded-md border border-[color:var(--color-neon-cyan-border-30)] px-3 py-2";

function formatAt(
  locale: string,
  value: string,
  options: Intl.DateTimeFormatOptions,
): string {
  return new Intl.DateTimeFormat(locale, options).format(new Date(value));
}

export function formatQueueTime(locale: string, value: string): string {
  return formatAt(locale, value, TIME_FORMAT);
}

export function formatQueueDate(locale: string, value: string): string {
  return formatAt(locale, value, DATE_FORMAT);
}
