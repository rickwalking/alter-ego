import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import { getRequestLocale } from "@/i18n/request-locale";
import "./globals.css";
import { QueryProvider } from "@/components/providers";
import { VercelInsights } from "@/components/vercel-insights";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  referrer: "no-referrer",
  title: "Pedro Marins · Alter Ego",
  description:
    "An intelligent assistant that knows everything about my career, experience, and skills. Dive into my knowledge base, explore carousels, and read curated tech content.",
  keywords: [
    "AI",
    "Blog",
    "Tech",
    "Software Engineering",
    "Next.js",
    "React",
    "Neon Shell",
  ],
  authors: [{ name: "Pedro Marins" }],
  openGraph: {
    title: "Pedro Marins · Alter Ego",
    description:
      "An intelligent assistant that knows everything about my career, experience, and skills. Dive into my knowledge base, explore carousels, and read curated tech content.",
    type: "website",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const messages = await getMessages();
  const locale = await getRequestLocale();

  return (
    // The whole app is dark-mode only. Tailwind's `dark:` variant resolves
    // against the `.dark` class on <html>, so setting it once here keeps
    // every dark-styled rule active without a toggle or provider.
    <html lang={locale} className="dark" suppressHydrationWarning>
      <body
        className={`${inter.variable} font-sans antialiased`}
        suppressHydrationWarning
      >
        <NextIntlClientProvider messages={messages}>
          <QueryProvider>{children}</QueryProvider>
        </NextIntlClientProvider>
        <VercelInsights />
      </body>
    </html>
  );
}
