import { NEON_CYAN, NEON_CYAN_DIM, TEXT_MUTED } from "@/constants/neon";

interface LoginHeroProps {
  title: string;
  subtitle: string;
}

export function LoginHero({ title, subtitle }: Readonly<LoginHeroProps>) {
  return (
    <div style={{ textAlign: "center", marginBottom: "32px" }}>
      <div
        style={{
          display: "inline-flex",
          alignItems: "center",
          gap: "8px",
          padding: "4px 12px",
          borderRadius: "4px",
          fontFamily: "'JetBrains Mono', ui-monospace, monospace",
          fontSize: "10px",
          fontWeight: 700,
          textTransform: "uppercase",
          letterSpacing: "2px",
          color: NEON_CYAN,
          background: NEON_CYAN_DIM,
          border: `1px solid rgba(0,212,255,0.15)`,
          marginBottom: "16px",
        }}
      >
        <span
          style={{
            width: "5px",
            height: "5px",
            borderRadius: "50%",
            background: NEON_CYAN,
            boxShadow: `0 0 6px ${NEON_CYAN}`,
          }}
        />
        Authentication
      </div>
      <h1
        style={{
          fontSize: "28px",
          fontWeight: 900,
          letterSpacing: "-0.03em",
          marginBottom: "8px",
        }}
      >
        {title}
      </h1>
      <p style={{ fontSize: "14px", color: TEXT_MUTED }}>{subtitle}</p>
    </div>
  );
}
