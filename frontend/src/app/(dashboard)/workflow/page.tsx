"use client";

import { useTranslations } from "next-intl";
import { WorkflowKanbanBoard } from "@/features/workflow/components/workflow-kanban-board";

export default function WorkflowBoardPage() {
  const t = useTranslations("workflow.board");

  return (
    <div className="container mx-auto py-8 px-4">
      <h1 className="text-2xl font-bold mb-6">{t("title")}</h1>
      <p className="text-muted-foreground mb-6">{t("subtitle")}</p>
      <WorkflowKanbanBoard />
    </div>
  );
}
