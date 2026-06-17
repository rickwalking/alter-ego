import { ScrollReveal } from "@/components/scroll-reveal";
import { TEXT_MUTED } from "@/constants/neon";
import type { MarketingStatsProps } from "@/app/(public)/(marketing)/types";

const STAT_VALUE_CLASS =
  "text-4xl font-black tracking-[-0.03em] text-neon-cyan leading-none [text-shadow:0_0_20px_rgba(0,212,255,0.15)]";

const STAT_LABEL_STYLE = {
  fontSize: "13px",
  color: TEXT_MUTED,
  marginTop: "6px",
  fontWeight: 500,
} as const;

export function MarketingStats({ t }: MarketingStatsProps): React.ReactElement {
  return (
    <ScrollReveal>
      <div
        className="mx-auto px-6"
        style={{ maxWidth: "1200px", position: "relative", zIndex: 1 }}
      >
        <div className="grid grid-cols-3 gap-6 py-10 px-12 border-t border-b border-[rgba(0,212,255,0.08)] bg-[rgba(0,212,255,0.02)] max-[900px]:grid-cols-1 max-[900px]:py-8 max-[900px]:px-6">
          <div style={{ textAlign: "center" }}>
            <div className={STAT_VALUE_CLASS}>8+</div>
            <div style={STAT_LABEL_STYLE}>{t("stats.years")}</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div className={STAT_VALUE_CLASS}>50+</div>
            <div style={STAT_LABEL_STYLE}>{t("stats.carousels")}</div>
          </div>
          <div style={{ textAlign: "center" }}>
            <div className={STAT_VALUE_CLASS}>∞</div>
            <div style={STAT_LABEL_STYLE}>{t("stats.topics")}</div>
          </div>
        </div>
      </div>
    </ScrollReveal>
  );
}
