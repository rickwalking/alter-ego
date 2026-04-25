export const SUPPORTED_LOCALES = ["en", "pt"] as const;
export const DEFAULT_LOCALE = "en" as const;
export type SupportedLocale = (typeof SUPPORTED_LOCALES)[number];
