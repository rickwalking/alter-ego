"use client";

import {
  BG_CARD,
  NEON_BORDER_DASHED,
  NEON_BORDER_DASHED_HOVER,
  NEON_BORDER_STRONG,
  NEON_HOVER_BG_CYAN,
} from "@/constants/neon";
import {
  PERSONA_COLORS,
  dimPersonaColor,
  type PersonaAccent,
  type PersonaData,
} from "@/app/dashboard/personas/constants";

function PersonaAvatar({
  initials,
  accent,
}: {
  initials: string;
  accent: PersonaAccent;
}): React.ReactElement {
  const color = PERSONA_COLORS[accent];
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
        background: dimPersonaColor(color),
        color,
      }}
    >
      {initials}
    </div>
  );
}

function TraitTag({ label }: { label: string }): React.ReactElement {
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
}): React.ReactElement {
  const isActive = status === "active";
  const color = isActive ? PERSONA_COLORS.teal : PERSONA_COLORS.amber;
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
        color,
        background: dimPersonaColor(color),
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
        }}
      />
      {status}
    </span>
  );
}

export function PersonaCard({ persona }: { persona: PersonaData }): React.ReactElement {
  return (
    <div
      style={{
        background: BG_CARD,
        border: "1px solid rgba(255,255,255,0.06)",
        borderRadius: 8,
        padding: 20,
        transition: "all 0.25s",
        cursor: "pointer",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = NEON_BORDER_STRONG;
        e.currentTarget.style.transform = "translateY(-2px)";
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = "rgba(255,255,255,0.06)";
        e.currentTarget.style.transform = "translateY(0)";
      }}
    >
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
          <div style={{ fontSize: 16, fontWeight: 700, color: "rgba(255,255,255,0.88)" }}>
            {persona.name}
          </div>
          <div style={{ fontSize: 12, color: "rgba(255,255,255,0.55)", marginTop: 2 }}>
            {persona.title}
          </div>
        </div>
      </div>
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
            color: "rgba(255,255,255,0.55)",
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

export interface CreatePersonaCardProps {
  onCreate?: () => void;
}

export function CreatePersonaCard({
  onCreate,
}: CreatePersonaCardProps): React.ReactElement {
  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onCreate}
      onKeyDown={(e) => {
        if ((e.key === "Enter" || e.key === " ") && onCreate) {
          onCreate();
        }
      }}
      style={{
        background: BG_CARD,
        border: `2px dashed ${NEON_BORDER_DASHED}`,
        borderRadius: 8,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        padding: 40,
        cursor: "pointer",
        transition: "all 0.25s",
      }}
      onMouseEnter={(e) => {
        e.currentTarget.style.borderColor = NEON_BORDER_DASHED_HOVER;
        e.currentTarget.style.background = NEON_HOVER_BG_CYAN;
      }}
      onMouseLeave={(e) => {
        e.currentTarget.style.borderColor = NEON_BORDER_STRONG;
        e.currentTarget.style.background = BG_CARD;
      }}
    >
      <div style={{ textAlign: "center", color: "rgba(255,255,255,0.55)" }}>
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
        <p style={{ fontSize: 12, margin: 0 }}>
          Define a new voice profile for your content pipeline.
        </p>
      </div>
    </div>
  );
}

export function PersonasEmptyState({
  searchQuery,
}: {
  searchQuery: string;
}): React.ReactElement {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "80px 20px",
        textAlign: "center",
        color: "rgba(255,255,255,0.55)",
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
  );
}
