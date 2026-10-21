import Link from "next/link";
import { getRequestLocale } from "@/i18n/request-locale";
import { getTranslations } from "next-intl/server";
import { LanguageSwitcher } from "@/components/language-switcher";
import { BG_DEEP, NEON_CYAN, TEXT, TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";

const PUBLIC_HEADER_MAX_WIDTH_PX = 1200;
const PUBLIC_HEADER_BRAND = "Pedro Marins";

const PUBLIC_HEADER_LINK_STYLE = {
  color: TEXT_MUTED,
  textDecoration: "none",
  fontSize: "14px",
  fontWeight: 500,
  transition: "color 0.2s",
} as const;

const PUBLIC_HEADER_NAV_ITEMS = [
  { href: PUBLIC_ROUTE_PATHS.CHAT, labelKey: "nav.chat" },
  { href: PUBLIC_ROUTE_PATHS.BLOG, labelKey: "nav.blog" },
  { href: PUBLIC_ROUTE_PATHS.CAROUSELS, labelKey: "nav.carousels" },
] as const;

type Translate = (key: string) => string;

interface PublicHeaderNavProps {
  t: Translate;
  locale: string;
}

export function PublicHeaderNav({
  t,
  locale,
}: PublicHeaderNavProps): React.ReactElement {
  return (
    <nav className="flex min-w-0 items-center gap-4 sm:gap-7">
      {PUBLIC_HEADER_NAV_ITEMS.map((item) => (
        <Link key={item.href} href={item.href} style={PUBLIC_HEADER_LINK_STYLE}>
          {t(item.labelKey)}
        </Link>
      ))}
      <div
        className="hidden sm:block"
        aria-hidden="true"
        style={{
          width: "1px",
          height: "20px",
          background: "rgba(0,212,255,0.15)",
        }}
      />
      <LanguageSwitcher currentLocale={locale} variant="neon" />
    </nav>
  );
}

export async function PublicHeader(): Promise<React.ReactElement> {
  const tc = await getTranslations("common");
  const locale = await getRequestLocale();

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
        className="mx-auto flex min-w-0 items-center justify-between gap-3 px-4 sm:px-6"
        style={{ maxWidth: `${PUBLIC_HEADER_MAX_WIDTH_PX}px` }}
      >
        <Link
          href={PUBLIC_ROUTE_PATHS.HOME}
          aria-label={PUBLIC_HEADER_BRAND}
          className="flex shrink-0 items-center gap-3"
          style={{
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
            aria-hidden="true"
          >
            P
          </span>
          <span className="hidden sm:inline">{PUBLIC_HEADER_BRAND}</span>
        </Link>
        <PublicHeaderNav t={tc} locale={locale} />
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
