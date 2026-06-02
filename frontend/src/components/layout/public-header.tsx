import Link from "next/link";
import { cookies } from "next/headers";
import { getTranslations } from "next-intl/server";
import { LanguageSwitcher } from "@/components/language-switcher";
import { BG_DEEP, NEON_CYAN, TEXT, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "@/i18n/config";
import type { SupportedLocale } from "@/i18n/config";

const PUBLIC_HEADER_MAX_WIDTH_PX = 1200;

export async function PublicHeader(): Promise<React.ReactElement> {
  const tc = await getTranslations("common");
  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const locale: SupportedLocale =
    localeCookie && SUPPORTED_LOCALES.includes(localeCookie as SupportedLocale)
      ? (localeCookie as SupportedLocale)
      : DEFAULT_LOCALE;

  return (
    <header
      className="sticky top-0 z-[100]"
      style={{
        padding: "16px 0",
        background: "rgba(6, 10, 18, 0.85)",
        backdropFilter: "blur(20px)",
        WebkitBackdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(0, 212, 255, 0.08)",
      }}
    >
      <div
        className="mx-auto px-6"
        style={{
          maxWidth: `${PUBLIC_HEADER_MAX_WIDTH_PX}px`,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Link
          href={PUBLIC_ROUTE_PATHS.HOME}
          style={{
            display: "flex",
            alignItems: "center",
            gap: "12px",
            fontSize: "20px",
            fontWeight: 800,
            color: TEXT,
            textDecoration: "none",
            letterSpacing: "-0.02em",
          }}
        >
          <span
            style={{
              width: "32px",
              height: "32px",
              border: `2px solid ${NEON_CYAN}`,
              borderRadius: "4px",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "14px",
              fontWeight: 700,
              color: NEON_CYAN,
              boxShadow:
                "0 0 12px rgba(0,212,255,0.15), inset 0 0 12px rgba(0,212,255,0.15)",
            }}
          >
            P
          </span>
          <span>Pedro Marins</span>
        </Link>
        <nav style={{ display: "flex", alignItems: "center", gap: "28px" }}>
          <Link
            href={PUBLIC_ROUTE_PATHS.CHAT}
            style={{
              color: TEXT_MUTED,
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: 500,
              transition: "color 0.2s",
            }}
          >
            {tc("nav.chat")}
          </Link>
          <Link
            href={PUBLIC_ROUTE_PATHS.BLOG}
            style={{
              color: TEXT_MUTED,
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: 500,
              transition: "color 0.2s",
            }}
          >
            {tc("nav.blog")}
          </Link>
          <Link
            href={PUBLIC_ROUTE_PATHS.LOGIN}
            style={{
              color: NEON_CYAN,
              textDecoration: "none",
              fontSize: "14px",
              fontWeight: 500,
              transition: "color 0.2s",
            }}
          >
            {tc("login")}
          </Link>
          <div
            style={{
              width: "1px",
              height: "20px",
              background: "rgba(0,212,255,0.15)",
            }}
          />
          <LanguageSwitcher currentLocale={locale} variant="neon" />
        </nav>
      </div>
    </header>
  );
}

/** Full-page wrapper for marketing/blog routes (header + scrollable main). */
export async function PublicShellFrame({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): Promise<React.ReactElement> {
  return (
    <div
      className="flex min-h-screen flex-col"
      style={{ background: BG_DEEP, position: "relative", zIndex: 1 }}
    >
      <PublicHeader />
      <main className="flex-1">{children}</main>
    </div>
  );
}
