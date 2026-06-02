"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";
import { NEON_CYAN, TEXT_DIM, TEXT_MUTED } from "@/constants/neon";

export const LOCALE_COOKIE_NAME = "locale";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 year

type LanguageSwitcherVariant = "default" | "neon";

interface LanguageSwitcherProps {
  currentLocale: string;
  variant?: LanguageSwitcherVariant;
}

export function LanguageSwitcher({
  currentLocale,
  variant = "default",
}: LanguageSwitcherProps) {
  const t = useTranslations("blog.languageSwitch");
  const [locale, setLocale] = useState(currentLocale);

  useEffect(() => {
    setLocale(currentLocale);
  }, [currentLocale]);

  const handleSwitch = (newLocale: string) => {
    if (newLocale === locale) return;

    document.cookie = `${LOCALE_COOKIE_NAME}=${newLocale}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`;
    window.location.reload();
  };

  if (variant === "neon") {
    const buttonBase: React.CSSProperties = {
      fontFamily: "'JetBrains Mono', ui-monospace, monospace",
      fontSize: "12px",
      fontWeight: 500,
      padding: "2px 6px",
      borderRadius: "4px",
      border: "none",
      background: "transparent",
      cursor: "pointer",
      transition: "all 0.2s",
    };

    return (
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: "4px",
        }}
        aria-label={t("label")}
        suppressHydrationWarning
      >
        <button
          type="button"
          onClick={() => handleSwitch("en")}
          style={{
            ...buttonBase,
            color: locale === "en" ? NEON_CYAN : TEXT_MUTED,
          }}
          aria-pressed={locale === "en"}
        >
          {t("en")}
        </button>
        <span style={{ color: TEXT_DIM, fontSize: "10px" }}>|</span>
        <button
          type="button"
          onClick={() => handleSwitch("pt")}
          style={{
            ...buttonBase,
            color: locale === "pt" ? NEON_CYAN : TEXT_MUTED,
          }}
          aria-pressed={locale === "pt"}
        >
          {t("pt")}
        </button>
      </div>
    );
  }

  return (
    <div
      className="flex items-center gap-1"
      aria-label={t("label")}
      suppressHydrationWarning
    >
      <button
        type="button"
        onClick={() => handleSwitch("pt")}
        className={`rounded px-2 py-1 text-xs font-bold uppercase tracking-wide transition-all ${
          locale === "pt"
            ? "bg-[var(--color-primary)]/20 text-[var(--color-primary)] border border-[var(--color-primary)]/30"
            : "text-[var(--color-muted-foreground)] border border-[var(--color-border)] hover:text-[var(--color-primary)]"
        }`}
        aria-pressed={locale === "pt"}
      >
        {t("pt")}
      </button>
      <button
        type="button"
        onClick={() => handleSwitch("en")}
        className={`rounded px-2 py-1 text-xs font-bold uppercase tracking-wide transition-all ${
          locale === "en"
            ? "bg-[var(--color-primary)]/20 text-[var(--color-primary)] border border-[var(--color-primary)]/30"
            : "text-[var(--color-muted-foreground)] border border-[var(--color-border)] hover:text-[var(--color-primary)]"
        }`}
        aria-pressed={locale === "en"}
      >
        {t("en")}
      </button>
    </div>
  );
}
