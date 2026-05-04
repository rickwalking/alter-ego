import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { cookies } from "next/headers";
import "./globals.css";
import { QueryProvider } from "@/components/providers";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "@/i18n/config";
import type { SupportedLocale } from "@/i18n/config";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "Pedro Marins - My Personal Blog and Assistant",
  description: "AI-generated carousels and blog posts about tech, AI, and software engineering.",
  keywords: ["AI", "Blog", "Tech", "Software Engineering", "Next.js", "React"],
  authors: [{ name: "Pedro Marins" }],
  openGraph: {
    title: "Pedro Marins - My Personal Blog and Assistant",
    description: "AI-generated carousels and blog posts about tech, AI, and software engineering.",
    type: "website",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const messages = await getMessages();
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const locale: SupportedLocale =
    localeCookie && SUPPORTED_LOCALES.includes(localeCookie as SupportedLocale)
      ? (localeCookie as SupportedLocale)
      : DEFAULT_LOCALE;

  return (
    // The whole app is dark-mode only. Tailwind's `dark:` variant resolves
    // against the `.dark` class on <html>, so setting it once here keeps
    // every dark-styled rule active without a toggle or provider.
    <html lang={locale} className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} font-sans antialiased`}>
        <NextIntlClientProvider messages={messages}>
          <QueryProvider>{children}</QueryProvider>
        </NextIntlClientProvider>
        <Analytics />
        <SpeedInsights />
      </body>
    </html>
  );
}
