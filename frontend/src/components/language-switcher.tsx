"use client";

import { useState, useEffect } from "react";
import { useTranslations } from "next-intl";

const COOKIE_NAME = "locale";
const COOKIE_MAX_AGE = 60 * 60 * 24 * 365; // 1 year

interface LanguageSwitcherProps {
  currentLocale: string;
}

export function LanguageSwitcher({ currentLocale }: LanguageSwitcherProps) {
  const t = useTranslations("blog.languageSwitch");
  const [locale, setLocale] = useState(currentLocale);

  useEffect(() => {
    setLocale(currentLocale);
  }, [currentLocale]);

  const handleSwitch = (newLocale: string) => {
    if (newLocale === locale) return;

    document.cookie = `${COOKIE_NAME}=${newLocale}; path=/; max-age=${COOKIE_MAX_AGE}; SameSite=Lax`;
    window.location.reload();
  };

  return (
    <div
      className="flex items-center gap-1"
      aria-label={t("label")}
      suppressHydrationWarning
    >
      <button
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
