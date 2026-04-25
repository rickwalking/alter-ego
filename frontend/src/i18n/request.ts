import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "./config";
import type { SupportedLocale } from "./config";

export default getRequestConfig(async () => {
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const locale: SupportedLocale =
    localeCookie && SUPPORTED_LOCALES.includes(localeCookie as SupportedLocale)
      ? (localeCookie as SupportedLocale)
      : DEFAULT_LOCALE;

  return {
    locale,
    messages: (await import(`./locales/${locale}.json`)).default,
  };
});
