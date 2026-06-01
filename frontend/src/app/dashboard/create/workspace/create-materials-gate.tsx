"use client";
import { NeonButton } from "@/components/atoms/neon-button";

import { useTranslations } from "next-intl";

interface CreateMaterialsGateProps {
  sourceCount: number;
  loading: boolean;
  onStartWithMaterials: () => void;
  onStartWithoutMaterials: () => void;
}

export function CreateMaterialsGate({
  sourceCount,
  loading,
  onStartWithMaterials,
  onStartWithoutMaterials,
}: CreateMaterialsGateProps): React.JSX.Element {
  const t = useTranslations("editorialWorkflow.gate");

  return (
    <div className="space-y-3 rounded-lg border border-dashed p-4">
      <h4 className="font-medium text-sm">{t("title")}</h4>
      <p className="text-sm" style={{ color: "rgba(255,255,255,0.55)" }}>
        {t("description")}
      </p>
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
