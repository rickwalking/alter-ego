"use client";

import Link from "next/link";
import { useTranslations } from "next-intl";
import { Container } from "./container";
import { LanguageSwitcher } from "@/components/language-switcher";
import { MobileNav } from "@/components/layout/mobile-nav";
import { NotificationCenter } from "@/features/workflow/components/notification-center";
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

  const editorLinks = isEditor ? (
    <>
      <Link
        href="/knowledge"
        className="transition-colors hover:text-[var(--color-primary)]"
      >
        {t("nav.knowledgeBase")}
      </Link>
      <Link
        href="/create"
        className="transition-colors hover:text-[var(--color-primary)]"
      >
        {t("nav.create")}
      </Link>
      <Link
        href="/personas"
        className="transition-colors hover:text-[var(--color-primary)]"
      >
        {t("nav.personas")}
      </Link>
      <Link
        href="/rubrics"
        className="transition-colors hover:text-[var(--color-primary)]"
      >
        {t("nav.rubrics")}
      </Link>
      <Link
        href="/blog-posts"
        className="transition-colors hover:text-[var(--color-primary)]"
      >
        {t("nav.blogPosts")}
      </Link>
      <Link
        href="/workflow"
        className="transition-colors hover:text-[var(--color-primary)]"
      >
        {t("nav.workflow")}
      </Link>
      <Link
        href="/calendar"
        className="transition-colors hover:text-[var(--color-primary)]"
      >
        {t("nav.calendar")}
      </Link>
      <Link
        href="/analytics"
        className="transition-colors hover:text-[var(--color-primary)]"
      >
        {t("nav.analytics")}
      </Link>
    </>
  ) : null;

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--color-border)] bg-[var(--color-background)]/95 backdrop-blur supports-[backdrop-filter]:bg-[var(--color-background)]/60">
      <Container>
        <div className="flex h-14 items-center justify-between">
          <div className="flex items-center gap-4 md:gap-6">
            <Link
              href="/"
              className="flex items-center gap-2 font-bold text-xl"
            >
              {t("appName")}
            </Link>
            <MobileNav />
            <nav className="hidden md:flex items-center gap-4 text-sm">
              <Link
                href="/chat"
                className="transition-colors hover:text-[var(--color-primary)]"
              >
                {t("nav.chat")}
              </Link>
              {editorLinks}
              <Link
                href="/blog"
                className="transition-colors hover:text-[var(--color-primary)]"
              >
                {t("nav.blog")}
              </Link>
              {isAdmin && (
                <Link
                  href="/admin/users"
                  className="transition-colors text-destructive"
                >
                  {t("nav.admin")}
                </Link>
              )}
            </nav>
          </div>
          <div className="flex items-center gap-4">
            <LanguageSwitcher currentLocale={currentLocale} />
            {isEditor && isAuthenticated && <NotificationCenter />}
            {!isLoading &&
              (isAuthenticated ? (
                <button
                  onClick={logout}
                  className="text-sm text-gray-600 hover:text-gray-900 transition-colors"
                >
                  {t("logout")}
                </button>
              ) : (
                <Link
                  href="/login"
                  className="text-sm text-primary hover:text-primary-800 transition-colors"
                >
                  {t("login")}
                </Link>
              ))}
          </div>
        </div>
      </Container>
    </header>
  );
}
