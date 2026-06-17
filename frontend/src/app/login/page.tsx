"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonFormField } from "@/components/molecules/neon-form-field";
import {
  NeonGridBackground,
  NeonScanlineOverlay,
} from "@/components/organisms";
import { AUTH_LOGIN_REDIRECT_PARAM } from "@/constants/auth";
import {
  BG_CARD,
  BG_DEEP,
  NEON_CYAN,
  NEON_CYAN_DIM,
  TEXT,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import { sanitizeLoginRedirect } from "@/modules/identity";

export default function LoginPage() {
  const t = useTranslations("auth");
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get("error") === "session_expired") {
      setError(t("sessionExpired"));
    }
  }, [t]);

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

      const params = new URLSearchParams(window.location.search);
      const redirectTo = sanitizeLoginRedirect(
        params.get(AUTH_LOGIN_REDIRECT_PARAM),
      );
      router.push(redirectTo);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loginError"));
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div
      className="min-h-screen flex flex-col"
      style={{
        background: BG_DEEP,
        color: TEXT,
        fontFamily: "Inter, system-ui, sans-serif",
      }}
    >
      <NeonGridBackground />
      <NeonScanlineOverlay />

      {/* Header */}
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

      {/* Login Form */}
      <main className="flex-1 flex items-center justify-center relative z-10 px-4">
        <div style={{ width: "100%", maxWidth: "420px" }}>
          <div style={{ textAlign: "center", marginBottom: "32px" }}>
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                padding: "4px 12px",
                borderRadius: "4px",
                fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                fontSize: "10px",
                fontWeight: 700,
                textTransform: "uppercase",
                letterSpacing: "2px",
                color: NEON_CYAN,
                background: NEON_CYAN_DIM,
                border: `1px solid rgba(0,212,255,0.15)`,
                marginBottom: "16px",
              }}
            >
              <span
                style={{
                  width: "5px",
                  height: "5px",
                  borderRadius: "50%",
                  background: NEON_CYAN,
                  boxShadow: `0 0 6px ${NEON_CYAN}`,
                }}
              />
              Authentication
            </div>
            <h1
              style={{
                fontSize: "28px",
                fontWeight: 900,
                letterSpacing: "-0.03em",
                marginBottom: "8px",
              }}
            >
              {t("loginTitle")}
            </h1>
            <p style={{ fontSize: "14px", color: TEXT_MUTED }}>
              {t("loginSubtitle")}
            </p>
          </div>

          <form
            onSubmit={(e) => {
              void handleSubmit(e);
            }}
            style={{
              background: BG_CARD,
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: "8px",
              padding: "32px",
            }}
          >
            {error && (
              <div
                style={{
                  marginBottom: "20px",
                  padding: "10px 14px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  background: "rgba(239,68,68,0.12)",
                  color: "#ef4444",
                  border: "1px solid rgba(239,68,68,0.15)",
                }}
              >
                {error}
              </div>
            )}

            <NeonFormField label={t("emailLabel")} name="email" required>
              <NeonInput
                id="email"
                name="email"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder={t("emailPlaceholder")}
              />
            </NeonFormField>

            <NeonFormField
              label={t("passwordLabel")}
              name="password"
              required
              className="mb-6"
            >
              <NeonInput
                id="password"
                name="password"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder={t("passwordPlaceholder")}
              />
            </NeonFormField>

            <NeonButton
              type="submit"
              fullWidth
              loading={isLoading}
              disabled={isLoading}
            >
              {isLoading ? t("signingIn") : t("signIn")}
            </NeonButton>
          </form>
        </div>
      </main>

      {/* Footer */}
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

      <style>{`
        @keyframes grid-drift {
          0% { transform: rotateX(60deg) translateY(0); }
          100% { transform: rotateX(60deg) translateY(60px); }
        }
      `}</style>
    </div>
  );
}
