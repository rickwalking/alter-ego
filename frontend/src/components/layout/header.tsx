"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Container } from "./container";
import { LanguageSwitcher } from "@/components/language-switcher";
import { DEFAULT_LOCALE } from "@/i18n/config";
import { useAuth } from "@/hooks/use-auth";

interface HeaderProps {
  locale?: string;
}

export function Header({ locale }: HeaderProps) {
  const t = useTranslations("common");
  const currentLocale = locale || DEFAULT_LOCALE;
  const { user, isAdmin, isEditor, logout, isLoading } = useAuth();

  const isAuthenticated = user !== null;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--color-border)] bg-[var(--color-background)]/95 backdrop-blur supports-[backdrop-filter]:bg-[var(--color-background)]/60">
      <Container>
        <div className="flex h-14 items-center justify-between">
          <div className="flex items-center gap-6">
            <Link
              href="/"
              className="flex items-center gap-2 font-bold text-xl"
            >
              {t("appName")}
            </Link>
            <nav className="hidden md:flex items-center gap-4 text-sm">
              <Link
                href="/chat"
                className="transition-colors hover:text-[var(--color-primary)]"
              >
                {t("nav.chat")}
              </Link>
              {isEditor && (
                <Link
                  href="/knowledge"
                  className="transition-colors hover:text-[var(--color-primary)]"
                >
                  {t("nav.knowledgeBase")}
                </Link>
              )}
              <Link
                href="/blog"
                className="transition-colors hover:text-[var(--color-primary)]"
              >
                {t("nav.blog")}
              </Link>
              {isEditor && (
                <Link
                  href="/create"
                  className="transition-colors hover:text-[var(--color-primary)]"
                >
                  {t("nav.create")}
                </Link>
              )}
              {isAdmin && (
                <Link
                  href="/admin/users"
                  className="transition-colors hover:text-[var(--color-primary)] text-destructive"
                >
                  Admin
                </Link>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <LanguageSwitcher currentLocale={currentLocale} />
            {!isLoading && (
              <>
                {isAuthenticated ? (
                  <button
                    onClick={logout}
                    className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
                  >
                    Logout
                  </button>
                ) : (
                  <Link
                    href="/login"
                    className="text-sm text-primary hover:text-primary-800 transition-colors"
                  >
                    Login
                  </Link>
                )}
              </>
            )}
          </div>
        </div>
      </Container>
    </header>
  );
}
