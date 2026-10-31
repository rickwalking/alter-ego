"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonEntityWorkspace } from "@/components/molecules/neon-entity-workspace";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NEON_RED } from "@/constants/neon";
import { useEntityEditor } from "@/lib/use-entity-editor";
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
/** Narrower side padding on a phone so the rubric cards keep their width. */
const PAGE_CONTENT_CLASS = "page-content px-4 py-6 sm:px-8";

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
          onDelete={rubric.is_default ? undefined : () => onDelete(rubric)}
        />
      ))}
    </>
  );
}

export default function RubricsPage(): React.ReactElement {
  const t = useTranslations("rubrics.page");
  const tDelete = useTranslations("rubrics.delete");
  const collection = useRubrics();
  const editor = useEntityEditor<QualityRubric, QualityRubricCreatePayload>(
    collection,
  );

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar
        title={t("title")}
        breadcrumb={[{ label: t("breadcrumb") }]}
        actions={
          editor.showingList && (
            <NeonButton
              size="sm"
              onClick={editor.listActions.onCreate}
              icon={<PlusIcon />}
            >
              {t("new")}
            </NeonButton>
          )
        }
      />

      <div className={PAGE_CONTENT_CLASS}>
        <NeonEntityWorkspace
          editor={editor}
          deleteT={tDelete}
          list={
            <RubricList
              rubrics={collection.rubrics}
              loading={collection.loading}
              failed={collection.error !== null}
              {...editor.listActions}
            />
          }
          renderForm={(rubric) => (
            <RubricForm rubric={rubric} {...editor.formActions} />
          )}
        />
      </div>
    </div>
  );
}
