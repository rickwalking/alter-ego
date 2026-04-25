import { cookies } from "next/headers";
import { Header } from "@/components/layout";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "@/i18n/config";
import type { SupportedLocale } from "@/i18n/config";

export default async function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const locale: SupportedLocale =
    localeCookie && SUPPORTED_LOCALES.includes(localeCookie as SupportedLocale)
      ? (localeCookie as SupportedLocale)
      : DEFAULT_LOCALE;

  return (
    <div className="min-h-full flex flex-col">
      <Header locale={locale} />
      <main className="flex-1">{children}</main>
    </div>
  );
}
