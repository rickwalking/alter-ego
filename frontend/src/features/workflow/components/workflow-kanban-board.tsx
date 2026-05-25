"use client";

import { useTranslations } from "next-intl";
import {
  Badge,
  Button,
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  Spinner,
} from "@/components/ui";
import { useWorkflowKanban } from "@/features/workflow/hooks/use-workflow-kanban";
import Link from "next/link";

function formatPhase(phase: string): string {
  return phase.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function WorkflowKanbanBoard() {
  const t = useTranslations("workflow");
  const { board, loading, error, refetch } = useWorkflowKanban();

  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <Spinner />
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8 text-red-500">
        <p>{error}</p>
        <Button
          variant="outline"
          onClick={() => void refetch()}
          className="mt-4"
        >
          {t("kanban.retry")}
        </Button>
      </div>
    );
  }

  if (!board) {
    return null;
  }

  return (
    <div className="overflow-x-auto pb-4 md:overflow-visible">
      <div className="flex flex-col md:flex-row gap-4 md:min-w-max">
        {board.columns.map((column) => (
          <Card key={column.phase} className="w-full md:w-72 shrink-0">
            <CardHeader className="pb-2">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                {formatPhase(column.phase)}
                <Badge variant="secondary">{column.cards.length}</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {column.cards.length === 0 && (
                <p className="text-xs text-muted-foreground">
                  {t("board.noProjects")}
                </p>
              )}
              {column.cards.map((card) => (
                <Link
                  key={card.id}
                  href={`/create/${card.id}`}
                  className="block rounded-md border p-3 hover:bg-muted/50 transition-colors"
                >
                  <p className="font-medium text-sm truncate">{card.title}</p>
                  <p className="text-xs text-muted-foreground truncate">
                    {card.topic}
                  </p>
                  <Badge variant="outline" className="mt-2 text-xs">
                    {card.phase_status}
                  </Badge>
                </Link>
              ))}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}
