import { useTranslations } from "next-intl";
import { RUBRIC_COLORS } from "@/modules/editorial-operations";
import { dimColor } from "@/app/dashboard/rubrics/helpers";
import { StatusPill } from "@/components/atoms/status-pill";

/** Marks the default rubric (the API's `is_default`). */
export function RubricDefaultBadge(): React.ReactElement {
  const t = useTranslations("rubrics.panel");
  const color = RUBRIC_COLORS.teal;
  return (
    <StatusPill
      label={t("default")}
      color={color}
      background={dimColor(color)}
    />
  );
}
