import { getRequestConfig } from "next-intl/server";
import { getRequestLocale } from "./request-locale";

export default getRequestConfig(async () => {
  const locale = await getRequestLocale();

  return {
    locale,
    messages: (await import(`./locales/${locale}.json`)).default,
  };
});
