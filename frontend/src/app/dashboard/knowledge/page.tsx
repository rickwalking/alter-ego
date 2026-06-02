"use client";

import { useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { KnowledgeBaseInterface } from "@/features/knowledge/components";

export default function KnowledgePage(): React.ReactElement {
  const t = useTranslations("knowledge");

  return (
    <div className="flex min-h-full flex-col">
      <NeonTopBar title={t("title", { defaultValue: "Knowledge Base" })} />
      <KnowledgeBaseInterface />
    </div>
  );
}
