import Link from "next/link";
import { getTranslations } from "next-intl/server";

export async function BackLink() {
  const t = await getTranslations("blog");

  return (
    <Link
      href="/blog"
      className="mb-8 inline-flex items-center gap-2 text-sm transition-colors hover:opacity-80"
      style={{ color: "var(--color-muted-foreground)" }}
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
      >
        <path d="m12 19-7-7 7-7" />
        <path d="M19 12H5" />
      </svg>
      {t("backToPosts")}
    </Link>
  );
}
