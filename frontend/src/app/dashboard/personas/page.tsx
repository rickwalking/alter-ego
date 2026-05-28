"use client";

import { useState } from "react";

/* ── Constants ─────────────────────────────────────────────────── */
const COLORS = {
  cyan: "#00d4ff",
  magenta: "#ff2770",
  teal: "#0ac5a8",
  amber: "#f59e0b",
  red: "#ef4444",
} as const;

interface PersonaData {
  initials: string;
  name: string;
  title: string;
  traits: string[];
  description: string;
  carousels: number;
  score: string;
  status: "active" | "inactive";
  accent: keyof typeof COLORS;
}

const PERSONAS: PersonaData[] = [
  {
    initials: "TS",
    name: "Tech Specialist",
    title: "Deep technical, data-driven voice",
    traits: ["Precise", "Data-heavy", "Technical", "Concise"],
    description:
      "Speaks to engineers with assumed knowledge. Uses correct terminology, cites benchmarks, avoids fluff. Ideal for deep-dive carousels and technical analysis.",
    carousels: 12,
    score: "94%",
    status: "active",
    accent: "cyan",
  },
  {
    initials: "EL",
    name: "Engineering Leader",
    title: "Strategic, big-picture voice",
    traits: ["Strategic", "High-level", "Opinionated", "Confident"],
    description:
      "Tailored for engineering managers and team leads. Focuses on tradeoffs, team impact, and architectural decisions with authority.",
    carousels: 8,
    score: "91%",
    status: "active",
    accent: "magenta",
  },
  {
    initials: "PM",
    name: "Product Manager",
    title: "Value-focused, business-aware",
    traits: ["Pragmatic", "Business-aware", "Clear", "Concise"],
    description:
      "Bridges technical depth with business value. Highlights ROI, timelines, and competitive positioning for decision-makers.",
    carousels: 5,
    score: "87%",
    status: "active",
    accent: "amber",
  },
  {
    initials: "SA",
    name: "Security Analyst",
    title: "Cautious, precise, risk-aware",
    traits: ["Risk-aware", "Methodical", "Cautious", "Detailed"],
    description:
      "Authoritative voice for security content. Emphasizes threat modeling, mitigation strategies, and compliance considerations.",
    carousels: 6,
    score: "89%",
    status: "inactive",
    accent: "teal",
  },
];

/* ── Helpers ────────────────────────────────────────────────────── */
function dimColor(hex: string): string {
  return `${hex}1F`;
}

/* ── Sub-components ─────────────────────────────────────────────── */
function PersonaAvatar({
  initials,
  accent,
}: {
  initials: string;
  accent: keyof typeof COLORS;
}) {
  const color = COLORS[accent];
  return (
    <div
      style={{
        width: 48,
        height: 48,
        borderRadius: 12,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
        fontSize: 20,
        fontWeight: 700,
        flexShrink: 0,
        background: dimColor(color),
        color,
      }}
    >
      {initials}
    </div>
  );
}

function TraitTag({ label }: { label: string }) {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        borderRadius: 4,
        fontSize: 10,
        fontWeight: 600,
        letterSpacing: "0.3px",
        textTransform: "uppercase",
        color: "rgba(255,255,255,0.55)",
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.06)",
      }}
    >
      {label}
    </span>
  );
}

function StatusBadge({
  status,
}: {
  status: "active" | "inactive";
}) {
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

function PersonaCard({ persona }: { persona: PersonaData }) {
  return (
    <div
      style={{
        background: "#0d1324",
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 8,
        padding: 20,
        transition: "all 0.25s",
        cursor: "pointer",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)";
        e.currentTarget.style.transform = "translateY(-2px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)";
        e.currentTarget.style.transform = "translateY(0)";
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 14,
          marginBottom: 14,
        }}
      >
        <PersonaAvatar initials={persona.initials} accent={persona.accent} />
        <div>
          <div
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: "var(--color-foreground, #ededed)",
            }}
          >
            {persona.name}
          </div>
          <div
            style={{
              fontSize: 12,
              color: "var(--color-muted-foreground, #7f7f7f)",
              marginTop: 2,
            }}
          >
            {persona.title}
          </div>
        </div>
      </div>

      {/* Body */}
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
          {persona.traits.map((trait) => (
            <TraitTag key={trait} label={trait} />
          ))}
        </div>
        <p
          style={{
            fontSize: 12,
            color: "rgba(255,255,255,0.38)",
            lineHeight: 1.6,
            margin: 0,
          }}
        >
          {persona.description}
        </p>
      </div>

      {/* Footer */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginTop: 14,
          paddingTop: 14,
          borderTop: "1px solid rgba(255,255,255,0.04)",
        }}
      >
        <div
          style={{
            display: "flex",
            gap: 16,
            fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)",
            fontSize: 10,
            color: "var(--color-muted-foreground, #7f7f7f)",
          }}
        >
          <span>{persona.carousels} carousels</span>
          <span>Score: {persona.score}</span>
        </div>
        <StatusBadge status={persona.status} />
      </div>
    </div>
  );
}

function CreatePersonaCard() {
  return (
    <div
      style={{
        background: "#0d1324",
        border: "2px dashed rgba(0,212,255,0.15)",
        borderRadius: 8,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 40,
        cursor: "pointer",
        transition: "all 0.25s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = "rgba(0,212,255,0.35)";
        e.currentTarget.style.background = "rgba(0,212,255,0.03)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(0,212,255,0.15)";
        e.currentTarget.style.background = "var(--color-card, #111318)";
      }}
    >
      <div style={{ textAlign: "center", color: "var(--color-muted-foreground, #7f7f7f)" }}>
        <svg
          width="32"
          height="32"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          style={{ margin: "0 auto 12px", display: "block", opacity: 0.4 }}
          aria-hidden="true"
        >
          <path d="M12 5v14" />
          <path d="M5 12h14" />
        </svg>
        <h4
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.45)",
            fontWeight: 600,
            margin: "0 0 4px",
          }}
        >
          Create Persona
        </h4>
        <p style={{ fontSize: 12, color: "inherit", margin: 0 }}>
          Define a new voice profile for your content pipeline.
        </p>
      </div>
    </div>
  );
}

/* ── Main Page ──────────────────────────────────────────────────── */
export default function PersonasPage() {
  const [searchQuery, setSearchQuery] = useState("");

  const filtered = PERSONAS.filter((p) =>
    p.name.toLowerCase().includes(searchQuery.toLowerCase()),
  );

  return (
    <div className="flex-1 text-white relative" style={{ fontFamily: "Inter, system-ui, sans-serif" }}>
      {/* Top Bar */}
      <div style={{ height: "56px", display: "flex", alignItems: "center", justifyContent: "space-between", padding: "0 32px", borderBottom: "1px solid rgba(0,212,255,0.06)", background: "rgba(6,10,18,0.6)", backdropFilter: "blur(12px)", position: "sticky", top: 0, zIndex: 30 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <h1 style={{ fontSize: "16px", fontWeight: 700, color: "rgba(255,255,255,0.88)", letterSpacing: "-0.02em" }}>Personas</h1>
          <div style={{ fontFamily: "'JetBrains Mono', ui-monospace, monospace", fontSize: "11px", color: "rgba(255,255,255,0.3)" }}>/ <span style={{ color: "rgba(255,255,255,0.55)" }}>voice profiles</span></div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          <input
            type="search"
            placeholder="Search personas..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{
              padding: "6px 14px",
              borderRadius: "6px",
              border: "1px solid rgba(0,212,255,0.08)",
              background: "rgba(0,0,0,0.2)",
              color: "rgba(255,255,255,0.55)",
              fontSize: "13px",
              width: "200px",
              outline: "none",
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            }}
          />
        </div>
      </div>

      <div className="page-content" style={{ padding: "24px 32px" }}>
      {/* Grid */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(340px, 1fr))",
          gap: 16,
        }}
      >
        {filtered.map((persona) => (
          <PersonaCard key={persona.name} persona={persona} />
        ))}
        <CreatePersonaCard />
      </div>

      {/* Empty state */}
      {filtered.length === 0 && (
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            padding: "80px 20px",
            textAlign: "center",
            color: "var(--color-muted-foreground, #7f7f7f)",
          }}
        >
          <svg
            width="56"
            height="56"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{ opacity: 0.2, marginBottom: 16 }}
            aria-hidden="true"
          >
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
            <circle cx="12" cy="7" r="4" />
          </svg>
          <h3
            style={{
              fontSize: 18,
              color: "rgba(255,255,255,0.45)",
              marginBottom: 8,
              fontWeight: 700,
            }}
          >
            No personas found
          </h3>
          <p style={{ fontSize: 13, maxWidth: 400, lineHeight: 1.6, margin: 0 }}>
            {searchQuery
              ? `No results for "${searchQuery}". Try a different search term.`
              : "Create your first persona to define a unique voice profile for your content pipeline."}
          </p>
        </div>
      )}
    </div>
    </div>
  );
}
