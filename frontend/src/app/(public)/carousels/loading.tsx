import { getTranslations } from "next-intl/server";
import { BG_DEEP } from "@/constants/neon";

const SKELETON_CARDS = 6;

export default async function CarouselsLoading(): Promise<React.ReactElement> {
  const t = await getTranslations("carousels");
  return (
    <div
      className="mx-auto px-4 py-12 sm:px-6"
      style={{ background: BG_DEEP }}
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">{t("loading")}</span>
      <div className="mb-10 h-10 w-64 animate-pulse rounded bg-white/5 motion-reduce:animate-none" />
      <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
        {Array.from({ length: SKELETON_CARDS }, (_, index) => (
          <div
            key={index}
            className="aspect-[4/5] animate-pulse rounded-lg bg-white/5 motion-reduce:animate-none"
          />
        ))}
      </div>
    </div>
  );
}
