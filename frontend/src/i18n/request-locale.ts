import { cookies, headers } from "next/headers";
import type { SupportedLocale } from "./config";
import { ACCEPT_LANGUAGE_HEADER, LOCALE_COOKIE, resolveLocale } from "./locale";

/** The locale of the current request (server only). */
export async function getRequestLocale(): Promise<SupportedLocale> {
  const [cookieStore, headerList] = await Promise.all([cookies(), headers()]);
  return resolveLocale({
    cookie: cookieStore.get(LOCALE_COOKIE)?.value,
    acceptLanguage: headerList.get(ACCEPT_LANGUAGE_HEADER),
  });
}
