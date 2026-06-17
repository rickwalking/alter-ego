import { ScrollReveal } from "@/components/scroll-reveal";
import {
  NEON_MAGENTA,
  NEON_PURPLE,
  NEON_TEAL,
  TEXT,
  TEXT_MUTED,
} from "@/constants/neon";
import { cn } from "@/lib/utils";
import { MarketingPrimaryFeature } from "@/app/(public)/(marketing)/marketing-primary-feature";
import { MarketingSectionEyebrow } from "@/app/(public)/(marketing)/marketing-section-eyebrow";
import type { MarketingFeaturesProps } from "@/app/(public)/(marketing)/types";

const FEATURE_SECONDARY_BASE =
  "landing-feature-secondary relative overflow-hidden rounded-xl border border-neon-card-border bg-bg-card p-9 min-w-0 transition-all duration-300 ease-[cubic-bezier(0.25,1,0.5,1)] before:content-[''] before:absolute before:top-0 before:inset-x-0 before:h-0.5 before:opacity-0 before:transition-opacity hover:before:opacity-100 hover:border-white/10";

interface SecondaryFeature {
  icon: string;
  title: string;
  desc: string;
  accent: string;
  accentClass: string;
}

function buildSecondaryFeatures(
  t: MarketingFeaturesProps["t"],
): SecondaryFeature[] {
  return [
    {
      icon: "M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1 0-5H20M8 7h8M8 11h6",
      title: t("features.blog.title"),
      desc: t("features.blog.description"),
      accent: NEON_TEAL,
      accentClass: cn(
        FEATURE_SECONDARY_BASE,
        "before:bg-neon-teal before:shadow-[0_0_12px_var(--color-neon-teal)]",
      ),
    },
    {
      icon: "M3 3h18v18H3zM8 8h8v8H8zM3 12h5M16 12h5M12 3v5M12 16v5",
      title: t("features.carousels.title"),
      desc: t("features.carousels.description"),
      accent: NEON_PURPLE,
      accentClass: cn(
        FEATURE_SECONDARY_BASE,
        "before:bg-neon-purple before:shadow-[0_0_12px_var(--color-neon-purple)]",
      ),
    },
  ];
}

function SecondaryFeatureCard({
  feat,
  testId,
}: {
  feat: SecondaryFeature;
  testId?: string;
}): React.ReactElement {
  return (
    <div className={feat.accentClass} data-testid={testId}>
      <div
        style={{
          width: "48px",
          height: "48px",
          borderRadius: "8px",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          marginBottom: "20px",
          background: `${feat.accent}1F`,
          color: feat.accent,
          fontSize: "22px",
        }}
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          {feat.icon
            .split("M")
            .filter(Boolean)
            .map((seg, j) => (
              <path key={j} d={`M${seg}`} />
            ))}
        </svg>
      </div>
      <h3 style={{ fontSize: "18px", fontWeight: 700, marginBottom: "10px" }}>
        {feat.title}
      </h3>
      <p style={{ fontSize: "14px", color: TEXT_MUTED, lineHeight: 1.7 }}>
        {feat.desc}
      </p>
    </div>
  );
}

function FeaturesHeader({ t }: MarketingFeaturesProps): React.ReactElement {
  return (
    <div style={{ marginBottom: "60px" }}>
      <MarketingSectionEyebrow label={t("capabilities.label")} />
      <h2
        style={{
          fontSize: "clamp(32px, 4vw, 48px)",
          fontWeight: 800,
          letterSpacing: "-0.02em",
          lineHeight: 1.15,
          color: TEXT,
        }}
      >
        {t("features.titlePrefix")}{" "}
        <span style={{ color: NEON_MAGENTA }}>
          {t("features.titleHighlight")}
        </span>
      </h2>
    </div>
  );
}

export function MarketingFeatures({
  t,
}: MarketingFeaturesProps): React.ReactElement {
  const secondaryFeatures = buildSecondaryFeatures(t);

  return (
    <ScrollReveal delay={200}>
      <section className="relative z-[1] pb-[100px] max-[600px]:pb-[60px]">
        <div className="mx-auto px-6" style={{ maxWidth: "1200px" }}>
          <FeaturesHeader t={t} />

          <div className="grid grid-cols-2 gap-6 min-w-0 max-[900px]:grid-cols-1">
            <MarketingPrimaryFeature t={t} />

            {secondaryFeatures.map((feat, featIndex) => (
              <SecondaryFeatureCard
                key={feat.title}
                feat={feat}
                testId={featIndex === 0 ? "feature-secondary-0" : undefined}
              />
            ))}
          </div>
        </div>
      </section>
    </ScrollReveal>
  );
}
