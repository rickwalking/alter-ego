import Link from "next/link";
import { useTranslations } from "next-intl";
import { Container } from "./container";

export function Header() {
  const t = useTranslations("common");

  return (
    <header className="sticky top-0 z-50 w-full border-b border-[var(--color-border)] bg-[var(--color-background)]/95 backdrop-blur supports-[backdrop-filter]:bg-[var(--color-background)]/60">
      <Container>
        <div className="flex h-14 items-center justify-between">
          <div className="flex items-center gap-6">
            <Link href="/" className="flex items-center gap-2 font-bold text-xl">
              {t("appName")}
            </Link>
            <nav className="hidden md:flex items-center gap-4 text-sm">
              <Link
                href="/chat"
                className="transition-colors hover:text-[var(--color-primary)]"
              >
                {t("nav.chat")}
              </Link>
              <Link
                href="/knowledge"
                className="transition-colors hover:text-[var(--color-primary)]"
              >
                {t("nav.knowledgeBase")}
              </Link>
              <Link
                href="/blog"
                className="transition-colors hover:text-[var(--color-primary)]"
              >
                {t("nav.blog")}
              </Link>
              <Link
                href="/create"
                className="transition-colors hover:text-[var(--color-primary)]"
              >
                {t("nav.create")}
              </Link>
            </nav>
          </div>
        </div>
      </Container>
    </header>
  );
}
