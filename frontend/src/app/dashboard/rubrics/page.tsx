"use client";

import { NeonButton } from "@/components/atoms/neon-button";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { RUBRICS } from "@/app/dashboard/rubrics/constants";
import { RubricPanel } from "@/app/dashboard/rubrics/rubric-panel";

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";
const PAGE_CONTENT_PADDING = "24px 32px";

export default function RubricsPage(): React.ReactElement {
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
        {RUBRICS.map((rubric) => (
          <RubricPanel key={rubric.title} rubric={rubric} />
        ))}
      </div>
    </div>
  );
}
