import { useLocale, useTranslations } from "next-intl";
import { NEON_BORDER_SUBTLE, TEXT_MUTED } from "@/constants/neon";
import { formatLocaleNumber } from "@/lib/locale-format";
import {
  RUBRIC_ROW_BORDER,
  RUBRIC_TABLE_HEADER_BG,
  type CriterionRow,
} from "@/modules/editorial-operations";
import type { ScoreLevel } from "@/app/dashboard/rubrics/helpers";
import { ScoreCell } from "@/app/dashboard/rubrics/score-cell";
import { useScoringScaleLabel } from "@/app/dashboard/rubrics/use-rubric-labels";

const MONO_FONT = "var(--font-mono, 'JetBrains Mono', monospace)";
const FOREGROUND = "var(--color-foreground, #ededed)";
/** Four columns from `sm` up; below it each criterion stacks. */
const COLUMNS = "sm:grid sm:grid-cols-[2fr_1fr_1fr_1fr] sm:gap-2";

interface ScoreColumnProps {
  /** The column heading, repeated next to the cell while the row is stacked. */
  heading: string;
  label: string;
  level: ScoreLevel;
}

function ScoreColumn({
  heading,
  label,
  level,
}: Readonly<ScoreColumnProps>): React.ReactElement {
  return (
    <div className="flex items-center gap-2 sm:justify-center">
      <span
        className="text-[10px] uppercase tracking-wider sm:hidden"
        style={{ color: TEXT_MUTED }}
      >
        {heading}
      </span>
      <ScoreCell label={label} level={level} />
    </div>
  );
}

function HeaderRow(): React.ReactElement {
  const t = useTranslations("rubrics.panel");
  return (
    <div
      className={`rubric-header-row hidden ${COLUMNS}`}
      style={{
        padding: "10px 20px",
        fontFamily: MONO_FONT,
        fontSize: 9,
        textTransform: "uppercase",
        letterSpacing: 2,
        color: TEXT_MUTED,
        borderBottom: `1px solid ${NEON_BORDER_SUBTLE}`,
        background: RUBRIC_TABLE_HEADER_BG,
      }}
    >
      <span style={{ textAlign: "left" }}>{t("criterion")}</span>
      <span style={{ textAlign: "center" }}>{t("excellent")}</span>
      <span style={{ textAlign: "center" }}>{t("good")}</span>
      <span style={{ textAlign: "center" }}>{t("poor")}</span>
    </div>
  );
}

interface CriterionLineProps {
  criterion: CriterionRow;
  last: boolean;
}

function CriterionLine({
  criterion,
  last,
}: Readonly<CriterionLineProps>): React.ReactElement {
  const t = useTranslations("rubrics.panel");
  const locale = useLocale();
  const scaleLabel = useScoringScaleLabel();
  const threshold = t("threshold", {
    percent: criterion.thresholdPercent,
    scale: scaleLabel(criterion.scoringScale),
  });
  return (
    <div
      className={`rubric-criterion flex flex-col gap-2 sm:items-center ${COLUMNS}`}
      style={{
        padding: "12px 0",
        borderBottom: last ? "none" : `1px solid ${RUBRIC_ROW_BORDER}`,
      }}
    >
      <div className="min-w-0 break-words">
        <div style={{ fontSize: 13, color: FOREGROUND, fontWeight: 500 }}>
          {criterion.name}
        </div>
        <div style={{ fontSize: 11, color: TEXT_MUTED }}>
          {criterion.description}
        </div>
        <div style={{ fontFamily: MONO_FONT, fontSize: 10, color: TEXT_MUTED }}>
          {t("weight", {
            weight: formatLocaleNumber(criterion.weight, locale),
          })}
        </div>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-2 sm:contents">
        <ScoreColumn
          heading={t("excellent")}
          label={threshold}
          level="excellent"
        />
        <ScoreColumn
          heading={t("good")}
          label={t("meetsThreshold")}
          level="good"
        />
        <ScoreColumn
          heading={t("poor")}
          label={t("belowThreshold")}
          level="poor"
        />
      </div>
    </div>
  );
}

interface RubricCriteriaTableProps {
  criteria: readonly CriterionRow[];
}

/** The criteria of a rubric card: a table from `sm` up, stacked rows below. */
export function RubricCriteriaTable({
  criteria,
}: Readonly<RubricCriteriaTableProps>): React.ReactElement {
  const t = useTranslations("rubrics.panel");
  return (
    <>
      <HeaderRow />
      <div style={{ padding: "0 20px" }}>
        {criteria.length === 0 && (
          <p className="py-3 text-xs" style={{ color: TEXT_MUTED }}>
            {t("noCriteria")}
          </p>
        )}
        {criteria.map((criterion, idx) => (
          <CriterionLine
            key={`${idx}-${criterion.name}`}
            criterion={criterion}
            last={idx === criteria.length - 1}
          />
        ))}
      </div>
    </>
  );
}
