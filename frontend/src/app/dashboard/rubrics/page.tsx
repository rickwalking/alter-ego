"use client";

/* ── Constants ─────────────────────────────────────────────────── */
const COLORS = {
  cyan: "#00d4ff",
  magenta: "#ff2770",
  teal: "#0ac5a8",
  amber: "#f59e0b",
  red: "#ef4444",
} as const;

interface CriterionRow {
  name: string;
  description: string;
  excellent: string;
  good: string;
  poor: string;
}

interface RubricData {
  badge: string;
  badgeColor: keyof typeof COLORS;
  title: string;
  weight: string;
  status: "active" | "inactive";
  criteria: CriterionRow[];
}

const RUBRICS: RubricData[] = [
  {
    badge: "Carousel",
    badgeColor: "cyan",
    title: "Content Quality Rubric",
    weight: "1.0",
    status: "active",
    criteria: [
      {
        name: "Technical Accuracy",
        description: "Facts, data, and claims are verifiable",
        excellent: "No errors",
        good: "Minor issues",
        poor: "Major errors",
      },
      {
        name: "Tone Alignment",
        description: "Matches persona voice and brand",
        excellent: "Fully aligned",
        good: "Mostly aligned",
        poor: "Off voice",
      },
      {
        name: "Visual Cohesion",
        description: "Design consistency across slides",
        excellent: "Seamless",
        good: "Minor inconsistencies",
        poor: "Breaks theme",
      },
      {
        name: "Engagement",
        description: "Hook, pacing, call to action",
        excellent: "Compelling",
        good: "Solid",
        poor: "Flat",
      },
      {
        name: "Forbidden Phrases",
        description: "No banned words or AI-isms",
        excellent: "Zero matches",
        good: "1-2 minor",
        poor: "3+ matches",
      },
    ],
  },
  {
    badge: "Blog",
    badgeColor: "magenta",
    title: "Blog Post Quality Rubric",
    weight: "1.0",
    status: "active",
    criteria: [
      {
        name: "Depth & Research",
        description: "Substance and sources",
        excellent: "Thorough",
        good: "Adequate",
        poor: "Shallow",
      },
      {
        name: "Readability",
        description: "Structure and flow",
        excellent: "Clear flow",
        good: "Readable",
        poor: "Hard to follow",
      },
      {
        name: "Originality",
        description: "Fresh perspective",
        excellent: "Novel insight",
        good: "Solid take",
        poor: "Generic",
      },
    ],
  },
];

/* ── Helpers ────────────────────────────────────────────────────── */
function dimColor(hex: string): string {
  return `${hex}1F`;
}

function getScoreClass(level: "excellent" | "good" | "fair" | "poor"): {
  bg: string;
  color: string;
} {
  const map: Record<string, { bg: string; color: string }> = {
    excellent: { bg: dimColor(COLORS.teal), color: COLORS.teal },
    good: { bg: dimColor(COLORS.cyan), color: COLORS.cyan },
    fair: { bg: dimColor(COLORS.amber), color: COLORS.amber },
    poor: { bg: dimColor(COLORS.red), color: COLORS.red },
  };
  return map[level];
}

/* ── Sub-components ─────────────────────────────────────────────── */
function Badge({
  label,
  color,
}: {
  label: string;
  color: keyof typeof COLORS;
}) {
  const c = COLORS[color];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        color: c,
        background: dimColor(c),
      }}
    >
      {label}
    </span>
  );
}

function StatusBadge({ status }: { status: "active" | "inactive" }) {
  const isActive = status === "active";
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 10px",
        borderRadius: 20,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        color: isActive ? COLORS.teal : COLORS.amber,
        background: isActive ? dimColor(COLORS.teal) : dimColor(COLORS.amber),
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: isActive ? COLORS.teal : COLORS.amber,
          display: "inline-block",
        }}
      />
      {status}
    </span>
  );
}

function ScoreCell({
  label,
  level,
}: {
  label: string;
  level: "excellent" | "good" | "poor";
}) {
  const { bg, color } = getScoreClass(level);
  return (
    <span
      style={{
        textAlign: "center",
        fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
        fontSize: 12,
        fontWeight: 700,
        padding: "4px 8px",
        borderRadius: 4,
        background: bg,
        color,
      }}
    >
      {label}
    </span>
  );
}

/* ── Main Page ──────────────────────────────────────────────────── */
export default function RubricsPage() {
  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      {/* Top Bar */}
      <div
        style={{
          height: "56px",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 32px",
          borderBottom: "1px solid rgba(0,212,255,0.06)",
          background: "rgba(6,10,18,0.6)",
          backdropFilter: "blur(12px)",
          position: "sticky",
          top: 0,
          zIndex: 30,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <h1
            style={{
              fontSize: "16px",
              fontWeight: 700,
              color: "rgba(255,255,255,0.88)",
              letterSpacing: "-0.02em",
            }}
          >
            Rubrics
          </h1>
          <div
            style={{
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "11px",
              color: "rgba(255,255,255,0.3)",
            }}
          >
            /{" "}
            <span style={{ color: "rgba(255,255,255,0.55)" }}>
              quality scoring
            </span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          <button
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 14px",
              borderRadius: "6px",
              fontSize: "12px",
              fontWeight: 600,
              border: "none",
              cursor: "pointer",
              fontFamily: "inherit",
              background: "linear-gradient(135deg, #00d4ff 0%, #0090b0 100%)",
              color: "#060a12",
              boxShadow: "0 0 16px rgba(0,212,255,0.15)",
            }}
          >
            <svg
              width="14"
              height="14"
              fill="none"
              stroke="currentColor"
              strokeWidth="2.5"
              viewBox="0 0 24 24"
            >
              <path d="M12 5v14" strokeLinecap="round" />
              <path d="M5 12h14" strokeLinecap="round" />
            </svg>
            New Rubric
          </button>
        </div>
      </div>

      <div className="page-content" style={{ padding: "24px 32px" }}>
        {RUBRICS.map((rubric) => (
          <div
            key={rubric.title}
            style={{
              background: "#0d1324",
              border: "1px solid rgba(255,255,255,0.06)",
              borderRadius: 8,
              overflow: "hidden",
              marginBottom: 16,
            }}
          >
            {/* Card Header */}
            <div
              style={{
                padding: "16px 20px",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                borderBottom: "1px solid rgba(255,255,255,0.04)",
                cursor: "pointer",
                transition: "background 0.2s",
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = "rgba(255,255,255,0.02)";
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
                <Badge label={rubric.badge} color={rubric.badgeColor} />
                {rubric.title}
                <span
                  style={{
                    fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
                    fontSize: 11,
                    color: "var(--color-muted-foreground, #7f7f7f)",
                    fontWeight: 400,
                  }}
                >
                  Weight: {rubric.weight}
                </span>
              </h3>
              <StatusBadge status={rubric.status} />
            </div>

            {/* Column Header Row */}
            <div
              className="rubric-header-row"
              style={{
                display: "grid",
                gridTemplateColumns: "2fr 1fr 1fr 1fr",
                gap: 8,
                padding: "10px 20px",
                fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
                fontSize: 9,
                textTransform: "uppercase",
                letterSpacing: 2,
                color: "var(--color-muted-foreground, #7f7f7f)",
                borderBottom: "1px solid rgba(0,212,255,0.06)",
                background: "rgba(0,0,0,0.15)",
              }}
            >
              <span style={{ textAlign: "left" }}>Criterion</span>
              <span style={{ textAlign: "center" }}>Excellent (4)</span>
              <span style={{ textAlign: "center" }}>Good (3)</span>
              <span style={{ textAlign: "center" }}>Poor (1-2)</span>
            </div>

            {/* Criteria Rows */}
            <div style={{ padding: "0 20px" }}>
              {rubric.criteria.map((c, idx) => (
                <div
                  key={c.name}
                  className="rubric-criterion"
                  style={{
                    display: "grid",
                    gridTemplateColumns: "2fr 1fr 1fr 1fr",
                    gap: 8,
                    padding: "12px 0",
                    borderBottom:
                      idx < rubric.criteria.length - 1
                        ? "1px solid rgba(255,255,255,0.03)"
                        : "none",
                    alignItems: "center",
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
                    <div
                      style={{
                        fontSize: 11,
                        color: "var(--color-muted-foreground, #7f7f7f)",
                      }}
                    >
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
        ))}
      </div>
    </div>
  );
}
