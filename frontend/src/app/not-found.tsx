import Link from "next/link";
import { getTranslations } from "next-intl/server";

export default async function NotFound() {
  const t = await getTranslations("notFound");

  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] text-center px-4">
      <h1 className="text-6xl font-bold text-[var(--color-primary)]">{t("code")}</h1>
      <h2 className="mt-4 text-2xl font-semibold">{t("title")}</h2>
      <p className="mt-2 text-[var(--color-muted-foreground)]">
        {t("description")}
      </p>
      <Link
        href="/"
        className="mt-8 inline-flex items-center justify-center rounded-md bg-[var(--color-primary)] text-[var(--color-primary-foreground)] px-6 py-3 font-medium hover:bg-[var(--color-primary)]/90"
      >
        {t("goHome")}
      </Link>
    </div>
  );
}
