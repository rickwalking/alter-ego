import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";
import { NextIntlClientProvider } from "next-intl";
import { getMessages } from "next-intl/server";
import "./globals.css";
import { QueryProvider } from "@/components/providers";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
});

export const metadata: Metadata = {
  title: "RAG Chat - Personal Knowledge Assistant",
  description: "Chat with an AI about your personal knowledge base",
  keywords: ["RAG", "AI", "Chat", "Knowledge Base", "Next.js", "React"],
  authors: [{ name: "RAG Chat Team" }],
  openGraph: {
    title: "RAG Chat - Personal Knowledge Assistant",
    description: "Chat with an AI about your personal knowledge base",
    type: "website",
  },
};

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const messages = await getMessages();

  return (
    // The whole app is dark-mode only. Tailwind's `dark:` variant resolves
    // against the `.dark` class on <html>, so setting it once here keeps
    // every dark-styled rule active without a toggle or provider.
    <html lang="en" className="dark" suppressHydrationWarning>
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
