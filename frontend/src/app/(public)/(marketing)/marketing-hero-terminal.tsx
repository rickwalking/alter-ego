import {
  NEON_CYAN,
  NEON_MAGENTA,
  NEON_TEAL,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import type { Translator } from "@/app/(public)/(marketing)/types";

const TERMINAL_LINE_BASE = {
  opacity: 0,
  animation: "terminal-type 0.6s ease-out forwards",
} as const;

/** The animated terminal mock shown in the hero's right column. */
export function MarketingHeroTerminal({
  t,
}: {
  t: Translator;
}): React.ReactElement {
  return (
    <div
      className="relative flex justify-center items-center min-w-0 max-[900px]:order-[-1]"
      data-testid="hero-terminal"
    >
      <div
        style={{
          position: "absolute",
          width: "400px",
          height: "400px",
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(0,212,255,0.04) 0%, transparent 70%)`,
          animation: "ring-pulse 4s ease-in-out infinite",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          width: "300px",
          height: "300px",
          borderRadius: "50%",
          background: `radial-gradient(circle, rgba(255,39,112,0.03) 0%, transparent 70%)`,
          animation: "ring-pulse 4s ease-in-out infinite 1s",
          pointerEvents: "none",
        }}
      />
      <div
        className="w-full max-w-[480px] max-[900px]:max-w-full"
        style={{
          background: "rgba(6,10,18,0.8)",
          border: `1px solid rgba(0,212,255,0.15)`,
          borderRadius: "8px",
          overflow: "hidden",
          backdropFilter: "blur(10px)",
          boxShadow: `0 0 40px rgba(0,212,255,0.05), 0 0 80px rgba(0,212,255,0.02)`,
        }}
      >
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "12px 16px",
            background: "rgba(0,212,255,0.04)",
            borderBottom: "1px solid rgba(0,212,255,0.08)",
          }}
        >
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: "#ff5f56",
            }}
          />
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: "#ffbd2e",
            }}
          />
          <span
            style={{
              width: "10px",
              height: "10px",
              borderRadius: "50%",
              background: "#27c93f",
            }}
          />
          <span
            style={{
              marginLeft: "auto",
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "11px",
              color: TEXT_DIM,
            }}
          >
            alter-ego/session — zsh
          </span>
        </div>
        <div
          style={{
            padding: "20px",
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: "13px",
            lineHeight: 1.8,
            color: TEXT_MUTED,
          }}
        >
          <div style={{ ...TERMINAL_LINE_BASE, animationDelay: "0.2s" }}>
            <span style={{ color: NEON_TEAL }}>$</span>{" "}
            <span style={{ color: NEON_CYAN }}>./connect</span> --persona pedro
            --mode immersive
          </div>
          <div style={{ ...TERMINAL_LINE_BASE, animationDelay: "0.8s" }}>
            <span style={{ color: TEXT_DIM }}>
              ▸ Initializing neural interface...
            </span>
          </div>
          <div style={{ ...TERMINAL_LINE_BASE, animationDelay: "1.4s" }}>
            <span style={{ color: TEXT_DIM }}>
              ▸ Loading knowledge graph...
            </span>{" "}
            <span style={{ color: NEON_TEAL }}>✓ 2.4k nodes</span>
          </div>
          <div style={{ ...TERMINAL_LINE_BASE, animationDelay: "2.0s" }}>
            <span style={{ color: TEXT_DIM }}>
              ▸ Syncing experience vectors...
            </span>{" "}
            <span style={{ color: NEON_TEAL }}>✓ 8 yrs</span>
          </div>
          <div style={{ ...TERMINAL_LINE_BASE, animationDelay: "2.6s" }}>
            <span style={{ color: NEON_MAGENTA }}>◆</span>{" "}
            <span style={{ color: NEON_CYAN }}>Alter-Ego</span>{" "}
            <span style={{ color: TEXT_DIM }}>{t("terminal.ready")}</span>
          </div>
          <div style={{ ...TERMINAL_LINE_BASE, animationDelay: "3.2s" }}>
            <span style={{ color: NEON_TEAL }}>$</span>{" "}
            <span
              style={{
                display: "inline-block",
                width: "8px",
                height: "15px",
                background: NEON_CYAN,
                verticalAlign: "text-bottom",
                animation: "blink-cursor 1s step-end infinite",
                animationDelay: "3.8s",
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
