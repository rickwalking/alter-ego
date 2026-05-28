"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import Link from "next/link";

const CYAN = "#00d4ff";
const CYAN_DIM = "rgba(0,212,255,0.12)";
const TEXT = "rgba(255,255,255,0.88)";
const TEXT_MUTED = "rgba(255,255,255,0.55)";
const TEXT_DIM = "rgba(255,255,255,0.3)";
const BG_DEEP = "#060a12";
const BG_CARD = "#0d1324";

export default function LoginPage() {
  const t = useTranslations("auth");
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        const data = await response.json().catch(() => ({}));
        throw new Error(data.detail || t("loginError"));
      }

      router.push("/dashboard/chat");
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loginError"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ background: BG_DEEP, color: TEXT, fontFamily: "Inter, system-ui, sans-serif" }}>
      {/* Grid Background */}
      <div className="fixed inset-0 pointer-events-none z-0" aria-hidden="true" style={{ perspective: "600px", overflow: "hidden" }}>
        <div className="absolute inset-[-50%] w-[200%] h-[200%]" style={{
          backgroundImage: `linear-gradient(rgba(0, 212, 255, 0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.025) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
          transform: "rotateX(60deg)",
          animation: "grid-drift 20s linear infinite",
        }} />
      </div>

      {/* Scanline Overlay */}
      <div className="fixed inset-0 pointer-events-none z-50" style={{
        background: "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 212, 255, 0.012) 2px, rgba(0, 212, 255, 0.012) 4px)",
      }} />

      {/* Header */}
      <header className="relative z-10" style={{ padding: "16px 0", background: "rgba(6,10,18,0.85)", backdropFilter: "blur(20px)", borderBottom: "1px solid rgba(0,212,255,0.08)" }}>
        <div className="mx-auto px-6" style={{ maxWidth: "1200px", display: "flex", alignItems: "center", justifyContent: "space-between" }}>
          <Link href="/" style={{ display: "flex", alignItems: "center", gap: "12px", fontSize: "20px", fontWeight: 800, color: TEXT, textDecoration: "none", letterSpacing: "-0.02em" }}>
            <span style={{ width: "32px", height: "32px", border: `2px solid ${CYAN}`, borderRadius: "4px", display: "flex", alignItems: "center", justifyContent: "center", fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: "14px", fontWeight: 700, color: CYAN, boxShadow: `0 0 12px rgba(0,212,255,0.15), inset 0 0 12px rgba(0,212,255,0.15)` }}>P</span>
            <span>Pedro Marins</span>
          </Link>
        </div>
      </header>

      {/* Login Form */}
      <main className="flex-1 flex items-center justify-center relative z-10 px-4">
        <div style={{ width: "100%", maxWidth: "420px" }}>
          <div style={{ textAlign: "center", marginBottom: "32px" }}>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "8px", padding: "4px 12px", borderRadius: "4px", fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: "10px", fontWeight: 700, textTransform: "uppercase", letterSpacing: "2px", color: CYAN, background: CYAN_DIM, border: `1px solid rgba(0,212,255,0.15)`, marginBottom: "16px" }}>
              <span style={{ width: "5px", height: "5px", borderRadius: "50%", background: CYAN, boxShadow: `0 0 6px ${CYAN}` }} />
              Authentication
            </div>
            <h1 style={{ fontSize: "28px", fontWeight: 900, letterSpacing: "-0.03em", marginBottom: "8px" }}>
              {t("loginTitle")}
            </h1>
            <p style={{ fontSize: "14px", color: TEXT_MUTED }}>
              {t("loginSubtitle")}
            </p>
          </div>

          <form onSubmit={handleSubmit} style={{ background: BG_CARD, border: "1px solid rgba(255,255,255,0.06)", borderRadius: "8px", padding: "32px" }}>
            {error && (
              <div style={{ marginBottom: "20px", padding: "10px 14px", borderRadius: "6px", fontSize: "13px", background: "rgba(239,68,68,0.12)", color: "#ef4444", border: "1px solid rgba(239,68,68,0.15)" }}>
                {error}
              </div>
            )}

            <div style={{ marginBottom: "20px" }}>
              <label htmlFor="email" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: TEXT, marginBottom: "6px" }}>
                {t("emailLabel")}
              </label>
              <input
                id="email"
                name="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("emailPlaceholder")}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.08)",
                  background: "rgba(6,10,18,0.45)",
                  color: TEXT,
                  fontSize: "14px",
                  outline: "none",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => e.target.style.borderColor = CYAN}
                onBlur={(e) => e.target.style.borderColor = "rgba(255,255,255,0.08)"}
              />
            </div>

            <div style={{ marginBottom: "24px" }}>
              <label htmlFor="password" style={{ display: "block", fontSize: "13px", fontWeight: 600, color: TEXT, marginBottom: "6px" }}>
                {t("passwordLabel")}
              </label>
              <input
                id="password"
                name="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t("passwordPlaceholder")}
                style={{
                  width: "100%",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  border: "1px solid rgba(255,255,255,0.08)",
                  background: "rgba(6,10,18,0.45)",
                  color: TEXT,
                  fontSize: "14px",
                  outline: "none",
                  transition: "border-color 0.2s",
                }}
                onFocus={(e) => e.target.style.borderColor = CYAN}
                onBlur={(e) => e.target.style.borderColor = "rgba(255,255,255,0.08)"}
              />
            </div>

            <button
              type="submit"
              disabled={isLoading}
              style={{
                width: "100%",
                padding: "12px",
                borderRadius: "6px",
                border: "none",
                background: `linear-gradient(135deg, ${CYAN} 0%, #0090b0 100%)`,
                color: BG_DEEP,
                fontSize: "14px",
                fontWeight: 700,
                cursor: isLoading ? "not-allowed" : "pointer",
                opacity: isLoading ? 0.6 : 1,
                fontFamily: "inherit",
                boxShadow: `0 0 16px rgba(0,212,255,0.15)`,
              }}
            >
              {isLoading ? t("signingIn") : t("signIn")}
            </button>
          </form>
        </div>
      </main>

      {/* Footer */}
      <footer className="relative z-10" style={{ borderTop: "1px solid rgba(0,212,255,0.06)", padding: "24px 0", background: "rgba(6,10,18,0.5)" }}>
        <div className="mx-auto px-6" style={{ maxWidth: "1200px", display: "flex", justifyContent: "space-between", alignItems: "center", fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: "11px", color: TEXT_DIM }}>
          <span>© 2026 Pedro Marins</span>
          <Link href="/" style={{ color: TEXT_MUTED, textDecoration: "none" }}>Back to Home</Link>
        </div>
      </footer>

      <style>{`
        @keyframes grid-drift {
          0% { transform: rotateX(60deg) translateY(0); }
          100% { transform: rotateX(60deg) translateY(60px); }
        }
      `}</style>
    </div>
  );
}
