"use client";

import {
  BG_CARD,
  NEON_BORDER_DASHED,
  NEON_BORDER_DASHED_HOVER,
  NEON_BORDER_STRONG,
  NEON_HOVER_BG_CYAN,
} from "@/constants/neon";

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
