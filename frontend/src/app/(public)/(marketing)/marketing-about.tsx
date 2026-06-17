import { ScrollReveal } from "@/components/scroll-reveal";
import { NEON_MAGENTA, TEXT } from "@/constants/neon";
import {
  AboutBio,
  AboutPortrait,
} from "@/app/(public)/(marketing)/marketing-about-bio";
import { MarketingSectionEyebrow } from "@/app/(public)/(marketing)/marketing-section-eyebrow";
import type { MarketingAboutProps } from "@/app/(public)/(marketing)/types";

function AboutHeader({ t }: MarketingAboutProps): React.ReactElement {
  return (
    <div style={{ marginBottom: "40px" }}>
      <MarketingSectionEyebrow label={t("about.label")} />
      <h2
        style={{
          fontSize: "clamp(32px, 4vw, 48px)",
          fontWeight: 800,
          letterSpacing: "-0.02em",
          lineHeight: 1.15,
          color: TEXT,
        }}
      >
        {t("about.titlePrefix")}
        <span style={{ color: NEON_MAGENTA }}>{t("about.titleHighlight")}</span>
      </h2>
    </div>
  );
}

export function MarketingAbout({ t }: MarketingAboutProps): React.ReactElement {
  return (
    <ScrollReveal delay={100}>
      <section className="relative z-[1] py-20 max-[600px]:py-0 max-[600px]:pb-[60px]">
        <div className="mx-auto px-6" style={{ maxWidth: "1200px" }}>
          <AboutHeader t={t} />
          <div className="grid grid-cols-2 gap-12 items-center min-w-0 max-[900px]:grid-cols-1">
            <AboutPortrait t={t} />
            <AboutBio t={t} />
          </div>
        </div>
      </section>
    </ScrollReveal>
  );
}
