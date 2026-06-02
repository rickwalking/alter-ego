"use client";

import { BG_CARD, NEON_BORDER_STRONG } from "@/constants/neon";
import type { PersonaData } from "@/app/dashboard/personas/constants";
import { PersonaAvatar } from "./persona-avatar";
import { TraitTag } from "./trait-tag";
import { StatusBadge } from "./status-badge";

export function PersonaCard({
  persona,
}: {
  persona: PersonaData;
}): React.ReactElement {
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
          <div
            style={{
              fontSize: 16,
              fontWeight: 700,
              color: "rgba(255,255,255,0.88)",
            }}
          >
            {persona.name}
          </div>
          <div
            style={{
              fontSize: 12,
              color: "rgba(255,255,255,0.55)",
              marginTop: 2,
            }}
          >
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
