"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NEON_RED } from "@/constants/neon";
import { RubricDeleteDialog } from "@/app/dashboard/rubrics/rubric-delete-dialog";
import { RubricForm } from "@/app/dashboard/rubrics/rubric-form";
import { RubricPanel } from "@/app/dashboard/rubrics/rubric-panel";
import { RubricsEmptyState } from "@/app/dashboard/rubrics/rubrics-empty-state";
import { mapQualityRubricToPanelData } from "@/modules/editorial-operations";
import {
  useRubrics,
  type QualityRubric,
  type QualityRubricCreatePayload,
} from "@/modules/quality";

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";
const PAGE_CONTENT_PADDING = "24px 32px";

type View =
  | { kind: "list" }
  | { kind: "create" }
  | { kind: "edit"; rubric: QualityRubric };

const LIST_VIEW: View = { kind: "list" };

function PlusIcon(): React.ReactElement {
  return (
    <svg
      width="14"
      height="14"
      fill="none"
      stroke="currentColor"
      strokeWidth="2.5"
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path d="M12 5v14" strokeLinecap="round" />
      <path d="M5 12h14" strokeLinecap="round" />
    </svg>
  );
}

interface RubricListProps {
  rubrics: QualityRubric[];
  loading: boolean;
  failed: boolean;
  onCreate: () => void;
  onEdit: (rubric: QualityRubric) => void;
  onDelete: (rubric: QualityRubric) => void;
}

function RubricList({
  rubrics,
  loading,
  failed,
  onCreate,
  onEdit,
  onDelete,
}: Readonly<RubricListProps>): React.ReactElement {
  const t = useTranslations("rubrics.page");
  if (loading) {
    return (
      <div className="flex justify-center py-12">
        <NeonSpinner size="lg" />
      </div>
    );
  }
  if (failed) {
    return (
      <p role="alert" className="text-center py-8" style={{ color: NEON_RED }}>
        {t("loadError")}
      </p>
    );
  }
  if (rubrics.length === 0) {
    return <RubricsEmptyState onCreate={onCreate} />;
  }
  return (
    <>
      {rubrics.map((rubric) => (
        <RubricPanel
          key={rubric.id}
          rubric={mapQualityRubricToPanelData(rubric)}
          onEdit={() => onEdit(rubric)}
          onDelete={() => onDelete(rubric)}
        />
      ))}
    </>
  );
}

export default function RubricsPage(): React.ReactElement {
  const t = useTranslations("rubrics.page");
  const {
    rubrics,
    loading,
    error,
    create,
    update,
    delete: remove,
  } = useRubrics();
  const [view, setView] = useState<View>(LIST_VIEW);
  const [deleting, setDeleting] = useState<QualityRubric | null>(null);
  const openCreate = (): void => setView({ kind: "create" });

  const handleSave = async (
    payload: QualityRubricCreatePayload,
  ): Promise<void> => {
    if (view.kind === "edit") {
      await update(view.rubric.id, payload);
    } else {
      await create(payload);
    }
    setView(LIST_VIEW);
  };

  const handleDelete = async (rubric: QualityRubric): Promise<void> => {
    await remove(rubric.id);
    setDeleting(null);
  };

  const editing = view.kind === "edit" ? view.rubric : undefined;

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar
        title={t("title")}
        breadcrumb={[{ label: t("breadcrumb") }]}
        actions={
          view.kind === "list" && (
            <NeonButton size="sm" onClick={openCreate} icon={<PlusIcon />}>
              {t("new")}
            </NeonButton>
          )
        }
      />

      <div className="page-content" style={{ padding: PAGE_CONTENT_PADDING }}>
        {view.kind === "list" ? (
          <RubricList
            rubrics={rubrics}
            loading={loading}
            failed={error !== null}
            onCreate={openCreate}
            onEdit={(rubric) => setView({ kind: "edit", rubric })}
            onDelete={setDeleting}
          />
        ) : (
          <RubricForm
            key={editing?.id ?? view.kind}
            rubric={editing}
            onSave={handleSave}
            onCancel={() => setView(LIST_VIEW)}
          />
        )}
      </div>

      {deleting && (
        <RubricDeleteDialog
          rubric={deleting}
          onConfirm={() => handleDelete(deleting)}
          onClose={() => setDeleting(null)}
        />
      )}
    </div>
  );
}
