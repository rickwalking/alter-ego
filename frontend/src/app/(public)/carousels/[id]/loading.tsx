import { getTranslations } from "next-intl/server";
import { BG_DEEP } from "@/constants/neon";

export default async function CarouselViewerLoading(): Promise<React.ReactElement> {
  const t = await getTranslations("carousels");
  return (
    <div
      className="mx-auto max-w-3xl px-4 py-12 sm:px-6"
      style={{ background: BG_DEEP }}
      role="status"
      aria-live="polite"
    >
      <span className="sr-only">{t("loading")}</span>
      <div className="mx-auto mb-8 h-8 w-2/3 animate-pulse rounded bg-white/5 motion-reduce:animate-none" />
      <div className="aspect-[4/5] w-full animate-pulse rounded-2xl bg-white/5 motion-reduce:animate-none" />
    </div>
  );
}
