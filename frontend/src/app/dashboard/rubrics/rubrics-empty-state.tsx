"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";

interface RubricsEmptyStateProps {
  onCreate: () => void;
}

/** Shown when no rubric exists yet: what a rubric is, plus the create action. */
export function RubricsEmptyState({
  onCreate,
}: Readonly<RubricsEmptyStateProps>): React.ReactElement {
  const t = useTranslations("rubrics.empty");
  return (
    <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-white/10 px-6 py-12 text-center">
      <h2 className="text-base font-semibold text-text-primary">
        {t("title")}
      </h2>
      <p className="max-w-sm text-sm text-text-muted">{t("body")}</p>
      <NeonButton variant="primary" size="sm" onClick={onCreate}>
        {t("action")}
      </NeonButton>
    </div>
  );
}
