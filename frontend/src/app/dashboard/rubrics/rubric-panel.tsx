import {
  BG_CARD,
  NEON_BORDER_SUBTLE,
  NEON_CARD_BORDER,
  TEXT_MUTED,
} from "@/constants/neon";
import {
  RUBRIC_HEADER_BORDER,
  RUBRIC_HEADER_HOVER_BG,
  RUBRIC_ROW_BORDER,
  RUBRIC_TABLE_HEADER_BG,
  type RubricData,
} from "@/modules/editorial-operations";
import { RubricBadge } from "@/app/dashboard/rubrics/rubric-badge";
import { RubricStatusBadge } from "@/app/dashboard/rubrics/rubric-status-badge";
import { ScoreCell } from "@/app/dashboard/rubrics/score-cell";

interface RubricPanelProps {
  rubric: RubricData;
}

export function RubricPanel({ rubric }: RubricPanelProps): React.ReactElement {
  return (
    <div
      style={{
        background: BG_CARD,
        border: `1px solid ${NEON_CARD_BORDER}`,
        borderRadius: 8,
        overflow: "hidden",
        marginBottom: 16,
      }}
    >
      <div
        style={{
          padding: "16px 20px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          borderBottom: `1px solid ${RUBRIC_HEADER_BORDER}`,
          cursor: "pointer",
          transition: "background 0.2s",
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = RUBRIC_HEADER_HOVER_BG;
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = "transparent";
        }}
      >
        <h3
          style={{
            fontSize: 15,
            fontWeight: 700,
            color: "var(--color-foreground, #ededed)",
            display: "flex",
            alignItems: "center",
            gap: 10,
            margin: 0,
          }}
        >
          <RubricBadge label={rubric.badge} color={rubric.badgeColor} />
          {rubric.title}
          <span
            style={{
              fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
              fontSize: 11,
              color: TEXT_MUTED,
              fontWeight: 400,
            }}
          >
            Weight: {rubric.weight}
          </span>
        </h3>
        <RubricStatusBadge status={rubric.status} />
      </div>

      <div
        className="rubric-header-row grid grid-cols-[2fr_1fr_1fr_1fr] gap-2"
        style={{
          padding: "10px 20px",
          fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
          fontSize: 9,
          textTransform: "uppercase",
          letterSpacing: 2,
          color: TEXT_MUTED,
          borderBottom: `1px solid ${NEON_BORDER_SUBTLE}`,
          background: RUBRIC_TABLE_HEADER_BG,
        }}
      >
        <span style={{ textAlign: "left" }}>Criterion</span>
        <span style={{ textAlign: "center" }}>Excellent (4)</span>
        <span style={{ textAlign: "center" }}>Good (3)</span>
        <span style={{ textAlign: "center" }}>Poor (1-2)</span>
      </div>

      <div style={{ padding: "0 20px" }}>
        {rubric.criteria.map((c, idx) => (
          <div
            key={c.name}
            className="rubric-criterion grid grid-cols-[2fr_1fr_1fr_1fr] items-center gap-2"
            style={{
              padding: "12px 0",
              borderBottom:
                idx < rubric.criteria.length - 1
                  ? `1px solid ${RUBRIC_ROW_BORDER}`
                  : "none",
            }}
          >
            <div>
              <div
                style={{
                  fontSize: 13,
                  color: "var(--color-foreground, #ededed)",
                  fontWeight: 500,
                }}
              >
                {c.name}
              </div>
              <div style={{ fontSize: 11, color: TEXT_MUTED }}>
                {c.description}
              </div>
            </div>
            <div style={{ display: "flex", justifyContent: "center" }}>
              <ScoreCell label={c.excellent} level="excellent" />
            </div>
            <div style={{ display: "flex", justifyContent: "center" }}>
              <ScoreCell label={c.good} level="good" />
            </div>
            <div style={{ display: "flex", justifyContent: "center" }}>
              <ScoreCell label={c.poor} level="poor" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
