import Link from "next/link";
import { NEON_CYAN, TEXT_MUTED } from "@/constants/neon";
import { MarketingHeroTerminal } from "@/app/(public)/(marketing)/marketing-hero-terminal";
import type { MarketingHeroProps } from "@/app/(public)/(marketing)/types";

export function MarketingHero({
  t,
  tc,
}: MarketingHeroProps): React.ReactElement {
  return (
    <section className="relative z-[1] min-h-[85vh] flex items-center py-[60px] max-[600px]:min-h-0 max-[600px]:py-10">
      <div className="max-w-[1200px] w-full mx-auto px-6 grid grid-cols-2 gap-[60px] items-center max-[900px]:grid-cols-1 max-[900px]:gap-10">
        <div className="min-w-0">
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "8px",
              padding: "6px 14px",
              borderRadius: "4px",
              fontFamily: "'JetBrains Mono', ui-monospace, monospace",
              fontSize: "11px",
              fontWeight: 700,
              textTransform: "uppercase",
              letterSpacing: "3px",
              color: NEON_CYAN,
              background: "rgba(0,212,255,0.15)",
              border: `1px solid rgba(0,212,255,0.2)`,
              marginBottom: "24px",
            }}
          >
            <span
              className="animate-[pulse-dot_2s_ease-in-out_infinite] motion-reduce:animate-none"
              style={{
                width: "6px",
                height: "6px",
                borderRadius: "50%",
                background: NEON_CYAN,
                boxShadow: `0 0 8px ${NEON_CYAN}`,
              }}
            />
            <span>{t("hero.badgeVersion")}</span>
          </div>
          <h1
            className="text-[clamp(40px,6vw,72px)] font-black leading-[1.05] tracking-[-0.03em] mb-5 text-text-primary break-words"
            data-testid="hero-heading"
          >
            <span className="hero-glitch" data-text={t("hero.titleLine1")}>
              {t("hero.titleLine1")}
            </span>
            <br />
            <span className="bg-gradient-to-br from-neon-cyan to-neon-magenta bg-clip-text text-transparent">
              {t("hero.titleHighlight")}
            </span>
          </h1>
          <p
            style={{
              fontSize: "18px",
              color: TEXT_MUTED,
              maxWidth: "480px",
              lineHeight: 1.7,
              marginBottom: "36px",
            }}
          >
            {t("hero.subtitle")}
          </p>
          <div className="flex gap-4 flex-wrap">
            <Link
              href="/chat"
              className="landing-cta-primary"
              data-testid="cta-primary"
            >
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
              </svg>
              {tc("startChatting")}
            </Link>
            <Link href="/blog" className="landing-cta-ghost">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.5"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20" />
              </svg>
              {t("hero.exploreBlog")}
            </Link>
          </div>
        </div>

        <MarketingHeroTerminal t={t} />
      </div>
    </section>
  );
}
