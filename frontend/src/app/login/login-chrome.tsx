import Link from "next/link";
import { NEON_CYAN, TEXT, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";

export function LoginHeader() {
  return (
    <header
      className="relative z-10"
      style={{
        padding: "16px 0",
        background: "rgba(6,10,18,0.85)",
        backdropFilter: "blur(20px)",
        borderBottom: "1px solid rgba(0,212,255,0.08)",
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
              boxShadow: `0 0 12px rgba(0,212,255,0.15), inset 0 0 12px rgba(0,212,255,0.15)`,
            }}
          >
            P
          </span>
          <span>Pedro Marins</span>
        </Link>
      </div>
    </header>
  );
}

export function LoginFooter() {
  return (
    <footer
      className="relative z-10"
      style={{
        borderTop: "1px solid rgba(0,212,255,0.06)",
        padding: "24px 0",
        background: "rgba(6,10,18,0.5)",
      }}
    >
      <div
        className="mx-auto px-6"
        style={{
          maxWidth: "1200px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: "11px",
          color: TEXT_DIM,
        }}
      >
        <span>© 2026 Pedro Marins</span>
        <Link href="/" style={{ color: TEXT_MUTED, textDecoration: "none" }}>
          Back to Home
        </Link>
      </div>
    </footer>
  );
}
