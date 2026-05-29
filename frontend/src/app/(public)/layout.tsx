import Link from "next/link";
import { NeonGridBackground, NeonScanlineOverlay } from "@/components/organisms";
import { BG_DEEP, NEON_CYAN, TEXT, TEXT_MUTED } from "@/constants/neon";

function LanguageSwitch() {
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: "4px",
        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
        fontSize: "12px",
      }}
    >
      <Link
        href="/"
        hrefLang="en"
        style={{
          color: "rgba(255,255,255,0.55)",
          textDecoration: "none",
          fontWeight: 500,
          padding: "2px 6px",
          borderRadius: "4px",
          transition: "all 0.2s",
        }}
      >
        EN
      </Link>
      <span style={{ color: "rgba(255,255,255,0.2)", fontSize: "10px" }}>
        |
      </span>
      <Link
        href="/"
        hrefLang="pt"
        style={{
          color: "rgba(255,255,255,0.55)",
          textDecoration: "none",
          fontWeight: 500,
          padding: "2px 6px",
          borderRadius: "4px",
          transition: "all 0.2s",
        }}
      >
        PT
      </Link>
    </div>
  );
}

export default function PublicLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="min-h-full flex flex-col" style={{ background: BG_DEEP }}>
      <NeonGridBackground />
      <NeonScanlineOverlay />

      {/* Neon Shell Header */}
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
            maxWidth: "1200px",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
          }}
        >
          <Link
            href="/"
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
              href="/dashboard/chat"
              style={{
                color: TEXT_MUTED,
                textDecoration: "none",
                fontSize: "14px",
                fontWeight: 500,
                position: "relative",
                transition: "color 0.2s",
              }}
            >
              Chat
            </Link>
            <Link
              href="/dashboard/blog-posts"
              style={{
                color: TEXT_MUTED,
                textDecoration: "none",
                fontSize: "14px",
                fontWeight: 500,
                position: "relative",
                transition: "color 0.2s",
              }}
            >
              Blog
            </Link>
            <Link
              href="/dashboard"
              style={{
                color: TEXT_MUTED,
                textDecoration: "none",
                fontSize: "14px",
                fontWeight: 500,
                position: "relative",
                transition: "color 0.2s",
              }}
            >
              Dashboard
            </Link>
            <Link
              href="/login"
              style={{
                color: NEON_CYAN,
                textDecoration: "none",
                fontSize: "14px",
                fontWeight: 500,
                position: "relative",
                transition: "color 0.2s",
              }}
            >
              Login
            </Link>
            <div
              style={{
                width: "1px",
                height: "20px",
                background: "rgba(0,212,255,0.15)",
              }}
            />
            <LanguageSwitch />
          </nav>
        </div>
      </header>

      <main className="flex-1" style={{ position: "relative", zIndex: 1 }}>
        {children}
      </main>
    </div>
  );
}
