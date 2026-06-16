"use client";

import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NEON_RED } from "@/constants/neon";
import { RubricPanel } from "@/app/dashboard/rubrics/rubric-panel";
import { mapQualityRubricToPanelData } from "@/modules/editorial-operations";
import { useRubrics } from "@/features/rubrics/hooks/use-rubrics";

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";
const PAGE_CONTENT_PADDING = "24px 32px";

export default function RubricsPage(): React.ReactElement {
  const { rubrics, loading, error, create, refetch } = useRubrics();

  const handleNewRubric = async (): Promise<void> => {
    const name = window.prompt("Rubric name");
    if (!name?.trim()) return;
    await create({
      name: name.trim(),
      applicable_content_types: ["carousel"],
      criteria: [],
    });
    await refetch();
  };

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar
        title="Rubrics"
        breadcrumb={[{ label: "quality scoring" }]}
        actions={
          <NeonButton
            size="sm"
            onClick={() => void handleNewRubric()}
            icon={
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
            }
          >
            New Rubric
          </NeonButton>
        }
      />

      <div className="page-content" style={{ padding: PAGE_CONTENT_PADDING }}>
        {loading && (
          <div className="flex justify-center py-12">
            <NeonSpinner size="lg" />
          </div>
        )}
        {error && !loading && (
          <p className="text-center py-8" style={{ color: NEON_RED }}>
            {error}
          </p>
        )}
        {!loading &&
          !error &&
          rubrics.map((rubric) => (
            <RubricPanel
              key={rubric.id}
              rubric={mapQualityRubricToPanelData(rubric)}
            />
          ))}
      </div>
    </div>
  );
}
