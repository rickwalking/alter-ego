"use client";

import { useTranslations } from "next-intl";
import {
  NeonAlert,
  NeonAlertDescription,
} from "@/components/molecules/neon-alert";
import { CarouselReprocessAction } from "./carousel-reprocess-action";
import { CarouselReprocessProgress } from "./carousel-reprocess-progress";
import type { CarouselReprocessProps } from "./types";

export function CarouselReprocess({
  capability,
  pending,
  canSubmit,
  error,
  onReprocess,
}: Readonly<CarouselReprocessProps>): React.ReactElement | null {
  const t = useTranslations("workflow.reprocess");
  if (!capability) {
    return error ? (
      <NeonAlert variant="destructive">
        <NeonAlertDescription>{error}</NeonAlertDescription>
      </NeonAlert>
    ) : null;
  }
  return (
    <section
      aria-label={t("title")}
      className="space-y-3 rounded-md border border-[color:var(--color-neon-cyan-border-30)] p-3"
    >
      {error && (
        <NeonAlert variant="destructive">
          <NeonAlertDescription>{error}</NeonAlertDescription>
        </NeonAlert>
      )}
      <CarouselReprocessAction
        capability={capability}
        pending={pending}
        canSubmit={canSubmit}
        onReprocess={onReprocess}
      />
      <CarouselReprocessProgress capability={capability} />
    </section>
  );
}
