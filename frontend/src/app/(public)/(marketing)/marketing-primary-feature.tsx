import { NEON_CYAN, NEON_MAGENTA, TEXT_MUTED } from "@/constants/neon";
import type { MarketingFeaturesProps } from "@/app/(public)/(marketing)/types";

export function MarketingPrimaryFeature({
  t,
}: MarketingFeaturesProps): React.ReactElement {
  return (
    <div className="col-span-2 grid grid-cols-2 gap-0 rounded-xl overflow-hidden border border-[rgba(0,212,255,0.12)] bg-bg-surface transition-all duration-300 ease-[cubic-bezier(0.25,1,0.5,1)] hover:border-[rgba(0,212,255,0.25)] hover:shadow-[0_0_30px_rgba(0,212,255,0.04)] max-[900px]:grid-cols-1">
      <div
        className="min-h-[280px] max-[900px]:min-h-[160px] max-[900px]:p-8"
        style={{
          background: `linear-gradient(135deg, rgba(0,212,255,0.05) 0%, rgba(255,39,112,0.03) 100%)`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: "48px",
        }}
      >
        <svg
          viewBox="0 0 80 80"
          fill="none"
          width="80"
          height="80"
          style={{ opacity: 0.8 }}
        >
          <rect
            x="4"
            y="4"
            width="72"
            height="72"
            rx="8"
            stroke="url(#chat-grad)"
            strokeWidth="1.5"
          />
          <path
            d="M24 32h32M24 40h24M24 48h16"
            stroke="url(#chat-grad)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <circle
            cx="56"
            cy="52"
            r="12"
            fill="rgba(0,212,255,0.08)"
            stroke="url(#chat-grad)"
            strokeWidth="1.5"
          />
          <path
            d="M52 52h8M56 48v8"
            stroke="url(#chat-grad)"
            strokeWidth="1.5"
            strokeLinecap="round"
          />
          <defs>
            <linearGradient id="chat-grad" x1="0" y1="0" x2="80" y2="80">
              <stop offset="0%" stopColor={NEON_CYAN} />
              <stop offset="100%" stopColor={NEON_MAGENTA} />
            </linearGradient>
          </defs>
        </svg>
      </div>
      <div
        style={{
          padding: "48px",
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
        }}
      >
        <span
          style={{
            display: "inline-flex",
            alignSelf: "flex-start",
            padding: "4px 10px",
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: "10px",
            textTransform: "uppercase",
            letterSpacing: "2px",
            borderRadius: "3px",
            marginBottom: "16px",
            fontWeight: 700,
            color: NEON_CYAN,
            background: "rgba(0,212,255,0.15)",
            border: `1px solid rgba(0,212,255,0.15)`,
          }}
        >
          AI Chat
        </span>
        <h3
          style={{
            fontSize: "24px",
            fontWeight: 800,
            marginBottom: "12px",
            letterSpacing: "-0.02em",
          }}
        >
          {t("features.chat.title")}
        </h3>
        <p style={{ color: TEXT_MUTED, fontSize: "15px", lineHeight: 1.7 }}>
          {t("features.chat.description")}
        </p>
      </div>
    </div>
  );
}
