import Link from "next/link";
import { getTranslations } from "next-intl/server";
import { TEXT_MUTED } from "@/constants/neon";
import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { BackArrowIcon } from "@/components/atoms/back-arrow-icon";

export async function BackLink() {
  const t = await getTranslations("blog");

  return (
    <Link
      href={PUBLIC_ROUTE_PATHS.BLOG}
      className="mb-8 inline-flex items-center gap-2 text-sm transition-colors hover:opacity-80"
      style={{ color: TEXT_MUTED }}
    >
      <BackArrowIcon />
      {t("backToPosts")}
    </Link>
  );
}
