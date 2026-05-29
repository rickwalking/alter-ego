"use client";

/* ── Color Constants ── */
const CYAN = "#00d4ff";
const MAGENTA = "#ff2770";
const TEAL = "#0ac5a8";
const AMBER = "#f59e0b";
const PURPLE = "#a855f7";
const GREEN = "#22c55e";

/* ── Approval Badge Config ── */
type ApprovalStatus = "pending" | "approved" | "rejected" | "awaiting_human";

const APPROVAL_STYLES: Record<ApprovalStatus, { bg: string; color: string }> = {
  pending: { bg: "rgba(245,158,11,0.12)", color: "#f59e0b" },
  approved: { bg: "rgba(34,197,94,0.12)", color: "#22c55e" },
  rejected: { bg: "rgba(239,68,68,0.12)", color: "#ef4444" },
  awaiting_human: { bg: "rgba(0,212,255,0.12)", color: "#00d4ff" },
};

/* ── Types ── */
interface CardData {
  title: string;
  description: string;
  phase: string;
  assignee: string;
  assigneeBg: string;
  assigneeColor: string;
  approvalStatus: ApprovalStatus;
}

interface ColumnData {
  id: string;
  label: string;
  color: string;
  cards: CardData[];
}

/* ── Column Data ── */
const COLUMNS: ColumnData[] = [
  {
    id: "brief",
    label: "Brief",
    color: "#a0a0a0",
    cards: [],
  },
  {
    id: "research",
    label: "Research",
    color: CYAN,
    cards: [
      {
        title: "DeepSeek V4 Analysis",
        description:
          "Research open-source LLM benchmarks, architecture innovations, and pricing strategy from Twitter, GitHub, and tech blogs.",
        phase: "research",
        assignee: "PM",
        assigneeBg: "rgba(0,212,255,0.12)",
        assigneeColor: CYAN,
        approvalStatus: "awaiting_human",
      },
    ],
  },
  {
    id: "outline",
    label: "Outline",
    color: TEAL,
    cards: [],
  },
  {
    id: "content",
    label: "Content",
    color: GREEN,
    cards: [
      {
        title: "SpaceX Starship Update",
        description:
          "Slide content for SpaceX carousel. 5/5 slides completed. Persona score: 78%",
        phase: "content",
        assignee: "AL",
        assigneeBg: "rgba(34,197,94,0.12)",
        assigneeColor: GREEN,
        approvalStatus: "approved",
      },
      {
        title: "AI Safety Regulations",
        description:
          "Drafting regulatory landscape carousel. 3/5 slides in progress.",
        phase: "content",
        assignee: "JD",
        assigneeBg: "rgba(10,197,168,0.12)",
        assigneeColor: TEAL,
        approvalStatus: "pending",
      },
    ],
  },
  {
    id: "design",
    label: "Design",
    color: MAGENTA,
    cards: [
      {
        title: "Cybersecurity Trends",
        description:
          "Design tokens generated. Color theme: cyberpunk. Design tokens and layout approved.",
        phase: "design",
        assignee: "SK",
        assigneeBg: "rgba(255,39,112,0.12)",
        assigneeColor: MAGENTA,
        approvalStatus: "awaiting_human",
      },
    ],
  },
  {
    id: "images",
    label: "Images",
    color: AMBER,
    cards: [],
  },
  {
    id: "final_review",
    label: "Final Review",
    color: PURPLE,
    cards: [
      {
        title: "Kubernetes Security Guide",
        description:
          "All phases complete. Ready for final approval. Persona score: 82%",
        phase: "final_review",
        assignee: "PM",
        assigneeBg: "rgba(168,85,247,0.12)",
        assigneeColor: PURPLE,
        approvalStatus: "awaiting_human",
      },
    ],
  },
];

/* ── Styles ── */
const styles = {
  pageContent: {
    padding: "24px",
  } as const,
  grid: {
    display: "grid",
    gridTemplateColumns: "repeat(6, 1fr)",
    gap: "16px",
    minHeight: "60vh",
  } as const,
  column: {
    background: "rgba(6,10,18,0.3)",
    border: "1px solid rgba(255,255,255,0.04)",
    borderRadius: "8px",
    display: "flex",
    flexDirection: "column" as const,
  },
  colHeader: {
    padding: "12px 16px",
    borderBottom: "1px solid rgba(0,212,255,0.06)",
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
  } as const,
  colTitle: {
    fontSize: "12px",
    fontWeight: 700,
    textTransform: "uppercase" as const,
    letterSpacing: "1px",
  } as const,
  colCount: {
    fontFamily:
      '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    fontSize: "10px",
    color: "rgba(255,255,255,0.4)",
    background: "rgba(255,255,255,0.04)",
    padding: "2px 8px",
    borderRadius: "10px",
    cursor: "pointer" as const,
    border: "none",
    outlineOffset: "2px",
  } as const,
  cardsContainer: {
    padding: "12px",
    display: "flex",
    flexDirection: "column" as const,
    gap: "10px",
    flex: 1,
    minWidth: 0,
  } as const,
  card: {
    background: "#0d1324",
    border: "1px solid rgba(255,255,255,0.06)",
    borderRadius: "6px",
    padding: "14px",
    cursor: "pointer" as const,
    transition: "border-color 0.2s, background 0.2s",
  } as const,
  cardTitle: {
    fontSize: "13px",
    fontWeight: 600,
    color: "#f8fafc",
    marginBottom: "6px",
    overflowWrap: "break-word" as const,
    wordBreak: "break-word" as const,
  } as const,
  cardDesc: {
    fontSize: "11px",
    color: "rgba(255,255,255,0.4)",
    lineHeight: "1.4",
    marginBottom: "10px",
    display: "-webkit-box",
    WebkitLineClamp: 2,
    WebkitBoxOrient: "vertical" as const,
    overflow: "hidden",
    overflowWrap: "break-word" as const,
    wordBreak: "break-word" as const,
  } as const,
  cardFooter: {
    display: "flex",
    alignItems: "center",
    justifyContent: "space-between",
    minWidth: 0,
  } as const,
  assignee: {
    width: "22px",
    height: "22px",
    borderRadius: "50%",
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    fontFamily:
      '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    fontSize: "9px",
    fontWeight: 700,
    flexShrink: 0 as const,
  } as const,
  tags: {
    display: "flex",
    gap: "4px",
    flexWrap: "wrap" as const,
    marginBottom: "6px",
  } as const,
  phaseBadge: {
    fontSize: "9px",
    padding: "2px 6px",
    borderRadius: "3px",
    fontFamily:
      '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
    background: "rgba(255,255,255,0.04)",
    color: "rgba(255,255,255,0.4)",
  } as const,
  dot: {
    width: "6px",
    height: "6px",
    borderRadius: "50%",
    background: "currentColor",
    display: "inline-block",
    flexShrink: 0 as const,
  } as const,
};

/* ── Sub-components ── */

function ApprovalBadge({ status }: { status: ApprovalStatus }) {
  const style = APPROVAL_STYLES[status];
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "4px",
        fontSize: "8px",
        padding: "1px 5px",
        borderRadius: "3px",
        fontFamily:
          '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace',
        background: style.bg,
        color: style.color,
        overflowWrap: "break-word",
        wordBreak: "break-word",
      }}
    >
      <span style={styles.dot} aria-hidden="true" />
      {status}
    </span>
  );
}

function BoardCard({ card }: { card: CardData }) {
  return (
    <div
      tabIndex={0}
      role="button"
      style={styles.card}
      className="group"
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)";
        e.currentTarget.style.background = "#111a30";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)";
        e.currentTarget.style.background = "#0d1324";
      }}
      onMouseDown={(e) => {
        e.currentTarget.style.transform = "scale(0.98)";
      }}
      onMouseUp={(e) => {
        e.currentTarget.style.transform = "scale(1)";
      }}
    >
      <div style={styles.tags}>
        <span style={styles.phaseBadge}>{card.phase}</span>
      </div>
      <div style={styles.cardTitle}>{card.title}</div>
      <div style={styles.cardDesc}>{card.description}</div>
      <div style={styles.cardFooter}>
        <div
          style={{
            ...styles.assignee,
            background: card.assigneeBg,
            color: card.assigneeColor,
          }}
          title={card.assignee}
        >
          {card.assignee}
        </div>
        <ApprovalBadge status={card.approvalStatus} />
      </div>
    </div>
  );
}

function BoardColumn({ column }: { column: ColumnData }) {
  return (
    <div style={styles.column}>
      <div style={styles.colHeader}>
        <h3 style={{ ...styles.colTitle, color: column.color }}>
          {column.label}
        </h3>
        <span
          tabIndex={0}
          role="button"
          style={styles.colCount}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.08)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "rgba(255,255,255,0.04)";
          }}
        >
          {column.cards.length}
        </span>
      </div>
      <div style={styles.cardsContainer}>
        {column.cards.map((card) => (
          <BoardCard key={card.title} card={card} />
        ))}
      </div>
    </div>
  );
}

/* ── Page ── */
export default function WorkflowBoardPage() {
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
            Workflow Board
          </h1>
          <div
            style={{
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "11px",
              color: "rgba(255,255,255,0.3)",
            }}
          >
            / <span style={{ color: "rgba(255,255,255,0.55)" }}>pipeline</span>
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
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
            New Card
          </button>
        </div>
      </div>
      <div style={styles.pageContent}>
        <div style={styles.grid}>
          {COLUMNS.map((column) => (
            <BoardColumn key={column.id} column={column} />
          ))}
        </div>
        <style>{`
        @media (max-width: 1200px) {
          div[style*="grid-template-columns: repeat(6, 1fr)"] {
            grid-template-columns: repeat(4, 1fr) !important;
          }
        }
        @media (max-width: 800px) {
          div[style*="grid-template-columns: repeat(6, 1fr)"] {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }
        @media (max-width: 500px) {
          div[style*="grid-template-columns: repeat(6, 1fr)"] {
            grid-template-columns: 1fr !important;
          }
        }
        [tabindex="0"]:focus-visible {
          outline: 2px solid #00d4ff !important;
          outline-offset: 2px !important;
        }
        [role="button"]:active {
          transform: scale(0.98);
        }
      `}</style>
      </div>
    </div>
  );
}
