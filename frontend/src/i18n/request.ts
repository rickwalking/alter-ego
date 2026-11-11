import type { AbstractIntlMessages } from "next-intl";
import { getRequestConfig } from "next-intl/server";
import type { SupportedLocale } from "./config";
import { isSupportedLocale } from "./locale";
import { getRequestLocale } from "./request-locale";

/**
 * The messages of one request. An explicit supported locale, passed as
 * `getTranslations({ locale })` (the Portuguese-only privacy policy), wins
 * over the visitor's locale (cookie, then Accept-Language).
 */
export default getRequestConfig(async ({ locale: explicit }) => {
  const locale: SupportedLocale = isSupportedLocale(explicit)
    ? explicit
    : await getRequestLocale();

  return {
    locale,
    messages: (
      (await import(`./locales/${locale}.json`)) as {
        default: AbstractIntlMessages;
      }
    ).default,
  };
});
