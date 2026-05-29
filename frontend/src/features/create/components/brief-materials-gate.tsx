"use client";
import { NeonButton } from "@/components/atoms/neon-button";

import { useTranslations } from "next-intl";

interface BriefMaterialsGateProps {
  sourceCount: number;
  loading: boolean;
  onStartWithMaterials: () => void;
  onStartWithoutMaterials: () => void;
}

export function BriefMaterialsGate({
  sourceCount,
  loading,
  onStartWithMaterials,
  onStartWithoutMaterials,
}: BriefMaterialsGateProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.gate");

  return (
    <div className="space-y-3 rounded-lg border border-dashed p-4">
      <h4 className="font-medium text-sm">{t("title")}</h4>
      <p className="text-muted-foreground text-sm">{t("description")}</p>
      <p className="text-sm">{t("sourceCount", { count: sourceCount })}</p>
      <div className="flex flex-wrap gap-2">
        <NeonButton
          size="sm"
          disabled={loading || sourceCount === 0}
          onClick={onStartWithMaterials}
          data-testid="start-with-materials"
        >
          {t("startWithMaterials")}
        </NeonButton>
        <NeonButton
          size="sm"
          variant="outline"
          disabled={loading}
          onClick={onStartWithoutMaterials}
          data-testid="start-without-materials"
        >
          {t("startWithoutMaterials")}
        </NeonButton>
      </div>
    </div>
  );
}
