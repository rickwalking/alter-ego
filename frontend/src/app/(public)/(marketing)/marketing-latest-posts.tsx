import { ScrollReveal } from "@/components/scroll-reveal";
import { NEON_AMBER, TEXT, TEXT_MUTED } from "@/constants/neon";
import {
  FeaturedPostCard,
  SecondaryPostLink,
} from "@/app/(public)/(marketing)/marketing-post-cards";
import { MarketingSectionEyebrow } from "@/app/(public)/(marketing)/marketing-section-eyebrow";
import type {
  LatestPostsHeaderProps,
  MarketingLatestPostsProps,
} from "@/app/(public)/(marketing)/types";

function LatestPostsHeader({
  t,
}: LatestPostsHeaderProps): React.ReactElement {
  return (
    <div style={{ marginBottom: "60px" }}>
      <MarketingSectionEyebrow label={t("posts.feedLabel")} />
      <h2
        style={{
          fontSize: "clamp(32px, 4vw, 48px)",
          fontWeight: 800,
          letterSpacing: "-0.02em",
          lineHeight: 1.15,
          color: TEXT,
        }}
      >
        {t("posts.titlePrefix")}{" "}
        <span style={{ color: NEON_AMBER }}>{t("posts.titleHighlight")}</span>
      </h2>
      <p
        style={{
          fontSize: "16px",
          color: TEXT_MUTED,
          marginTop: "12px",
          maxWidth: "540px",
        }}
      >
        {t("posts.subtitle")}
      </p>
    </div>
  );
}

export function MarketingLatestPosts({
  t,
  tb,
  data,
  locale,
}: MarketingLatestPostsProps): React.ReactElement {
  const featured = data.items[0];
  return (
    <ScrollReveal delay={100}>
      <section className="relative z-[1] pb-[100px] max-[600px]:pb-[60px]">
        <div className="mx-auto px-6" style={{ maxWidth: "1200px" }}>
          <LatestPostsHeader t={t} />

          {data.items.length === 0 ? (
            <div
              style={{
                borderRadius: "12px",
                border: "1px dashed rgba(255,255,255,0.1)",
                padding: "48px",
                textAlign: "center",
              }}
            >
              <p style={{ fontSize: "16px", color: TEXT_MUTED }}>
                {tb("noPosts")}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-[1.3fr_0.7fr] gap-6 min-w-0 max-[900px]:grid-cols-1">
              <FeaturedPostCard post={featured} locale={locale} />

              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                {data.items.slice(1, 5).map((post) => (
                  <SecondaryPostLink
                    key={post.id}
                    post={post}
                    locale={locale}
                  />
                ))}
              </div>
            </div>
          )}
        </div>
      </section>
    </ScrollReveal>
  );
}
