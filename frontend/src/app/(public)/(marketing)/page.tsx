import Link from "next/link";
import Image from "next/image";
import { getTranslations } from "next-intl/server";
import { cookies } from "next/headers";
import { fetchCompletedProjects } from "@/lib/server-fetch";
import { FALLBACK_DESIGN_TOKENS } from "@/constants/blog";
import { DEFAULT_LOCALE, SUPPORTED_LOCALES } from "@/i18n/config";
import type { SupportedLocale } from "@/i18n/config";
import type { CarouselProjectListResponse } from "@/schemas/carousel";
import { ParticleBackground } from "@/components/particle-background";
import { ScrollReveal } from "@/components/scroll-reveal";
import {
  BG_SURFACE,
  NEON_AMBER,
  NEON_CYAN,
  NEON_MAGENTA,
  NEON_PURPLE,
  NEON_TEAL,
  TEXT,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import { toPublicCarouselImageUrl } from "@/lib/carousel-media-url";
import { cn } from "@/lib/utils";

const FEATURE_SECONDARY_BASE =
  "landing-feature-secondary relative overflow-hidden rounded-xl border border-neon-card-border bg-bg-card p-9 min-w-0 transition-all duration-300 ease-[cubic-bezier(0.25,1,0.5,1)] before:content-[''] before:absolute before:top-0 before:inset-x-0 before:h-0.5 before:opacity-0 before:transition-opacity hover:before:opacity-100 hover:border-white/10";

function truncateWords(text: string, maxWords: number): string {
  const cleaned = text.replace(/\*\*|\*|__|\`|\[|\]|\(|\)/g, "").trim();
  const words = cleaned.split(/\s+/).filter((w) => w.length > 0);
  if (words.length <= maxWords) return cleaned;
  return words.slice(0, maxWords).join(" ") + "...";
}

function HomePageContent({
  t,
  tc,
  tb,
  data,
  locale,
  fallback: _fallback,
}: {
  t: ReturnType<typeof getTranslations> extends Promise<infer R> ? R : never;
  tc: ReturnType<typeof getTranslations> extends Promise<infer R> ? R : never;
  tb: ReturnType<typeof getTranslations> extends Promise<infer R> ? R : never;
  data: CarouselProjectListResponse;
  locale: string;
  fallback: typeof FALLBACK_DESIGN_TOKENS;
}) {
  return (
    <>
      {/* Grid Background */}
      <div
        className="fixed inset-0 pointer-events-none z-0"
        aria-hidden="true"
        style={{ perspective: "600px", overflow: "hidden" }}
      >
        <div
          className="absolute inset-[-50%] w-[200%] h-[200%]"
          style={{
            backgroundImage: `linear-gradient(rgba(0, 212, 255, 0.025) 1px, transparent 1px), linear-gradient(90deg, rgba(0, 212, 255, 0.025) 1px, transparent 1px)`,
            backgroundSize: "60px 60px",
            transform: "rotateX(60deg)",
            animation: "grid-drift 20s linear infinite",
          }}
        />
      </div>

      {/* Scanline Overlay */}
      <div
        className="fixed inset-0 pointer-events-none z-50"
        style={{
          background:
            "repeating-linear-gradient(0deg, transparent, transparent 2px, rgba(0, 212, 255, 0.012) 2px, rgba(0, 212, 255, 0.012) 4px)",
        }}
      />

      {/* Particles */}
      <ParticleBackground />

      {/* Hero */}
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

          {/* Terminal Visual */}
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
                <div
                  style={{
                    opacity: 0,
                    animation: "terminal-type 0.6s ease-out forwards",
                    animationDelay: "0.2s",
                  }}
                >
                  <span style={{ color: NEON_TEAL }}>$</span>{" "}
                  <span style={{ color: NEON_CYAN }}>./connect</span> --persona
                  pedro --mode immersive
                </div>
                <div
                  style={{
                    opacity: 0,
                    animation: "terminal-type 0.6s ease-out forwards",
                    animationDelay: "0.8s",
                  }}
                >
                  <span style={{ color: TEXT_DIM }}>
                    ▸ Initializing neural interface...
                  </span>
                </div>
                <div
                  style={{
                    opacity: 0,
                    animation: "terminal-type 0.6s ease-out forwards",
                    animationDelay: "1.4s",
                  }}
                >
                  <span style={{ color: TEXT_DIM }}>
                    ▸ Loading knowledge graph...
                  </span>{" "}
                  <span style={{ color: NEON_TEAL }}>✓ 2.4k nodes</span>
                </div>
                <div
                  style={{
                    opacity: 0,
                    animation: "terminal-type 0.6s ease-out forwards",
                    animationDelay: "2.0s",
                  }}
                >
                  <span style={{ color: TEXT_DIM }}>
                    ▸ Syncing experience vectors...
                  </span>{" "}
                  <span style={{ color: NEON_TEAL }}>✓ 8 yrs</span>
                </div>
                <div
                  style={{
                    opacity: 0,
                    animation: "terminal-type 0.6s ease-out forwards",
                    animationDelay: "2.6s",
                  }}
                >
                  <span style={{ color: NEON_MAGENTA }}>◆</span>{" "}
                  <span style={{ color: NEON_CYAN }}>Alter-Ego</span>{" "}
                  <span style={{ color: TEXT_DIM }}>{t("terminal.ready")}</span>
                </div>
                <div
                  style={{
                    opacity: 0,
                    animation: "terminal-type 0.6s ease-out forwards",
                    animationDelay: "3.2s",
                  }}
                >
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
        </div>
      </section>

      {/* Stats Bar */}
      <ScrollReveal>
        <div
          className="mx-auto px-6"
          style={{ maxWidth: "1200px", position: "relative", zIndex: 1 }}
        >
          <div className="grid grid-cols-3 gap-6 py-10 px-12 border-t border-b border-[rgba(0,212,255,0.08)] bg-[rgba(0,212,255,0.02)] max-[900px]:grid-cols-1 max-[900px]:py-8 max-[900px]:px-6">
            <div style={{ textAlign: "center" }}>
              <div className="text-4xl font-black tracking-[-0.03em] text-neon-cyan leading-none [text-shadow:0_0_20px_rgba(0,212,255,0.15)]">
                8+
              </div>
              <div
                style={{
                  fontSize: "13px",
                  color: TEXT_MUTED,
                  marginTop: "6px",
                  fontWeight: 500,
                }}
              >
                {t("stats.years")}
              </div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div className="text-4xl font-black tracking-[-0.03em] text-neon-cyan leading-none [text-shadow:0_0_20px_rgba(0,212,255,0.15)]">
                50+
              </div>
              <div
                style={{
                  fontSize: "13px",
                  color: TEXT_MUTED,
                  marginTop: "6px",
                  fontWeight: 500,
                }}
              >
                {t("stats.carousels")}
              </div>
            </div>
            <div style={{ textAlign: "center" }}>
              <div className="text-4xl font-black tracking-[-0.03em] text-neon-cyan leading-none [text-shadow:0_0_20px_rgba(0,212,255,0.15)]">
                ∞
              </div>
              <div
                style={{
                  fontSize: "13px",
                  color: TEXT_MUTED,
                  marginTop: "6px",
                  fontWeight: 500,
                }}
              >
                {t("stats.topics")}
              </div>
            </div>
          </div>
        </div>
      </ScrollReveal>

      {/* Features */}
      <ScrollReveal delay={200}>
        <section className="relative z-[1] pb-[100px] max-[600px]:pb-[60px]">
          <div className="mx-auto px-6" style={{ maxWidth: "1200px" }}>
            <div style={{ marginBottom: "60px" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "3px",
                  color: NEON_CYAN,
                  marginBottom: "12px",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "1px",
                    background: NEON_CYAN,
                    boxShadow: `0 0 8px ${NEON_CYAN}`,
                  }}
                />
                {t("capabilities.label")}
              </div>
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

            <div className="grid grid-cols-2 gap-6 min-w-0 max-[900px]:grid-cols-1">
              {/* Primary Feature */}
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
                      <linearGradient
                        id="chat-grad"
                        x1="0"
                        y1="0"
                        x2="80"
                        y2="80"
                      >
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
                  <p
                    style={{
                      color: TEXT_MUTED,
                      fontSize: "15px",
                      lineHeight: 1.7,
                    }}
                  >
                    {t("features.chat.description")}
                  </p>
                </div>
              </div>

              {/* Secondary Features */}
              {[
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
              ].map((feat, featIndex) => (
                <div
                  key={feat.title}
                  className={feat.accentClass}
                  data-testid={
                    featIndex === 0 ? "feature-secondary-0" : undefined
                  }
                >
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
                  <h3
                    style={{
                      fontSize: "18px",
                      fontWeight: 700,
                      marginBottom: "10px",
                    }}
                  >
                    {feat.title}
                  </h3>
                  <p
                    style={{
                      fontSize: "14px",
                      color: TEXT_MUTED,
                      lineHeight: 1.7,
                    }}
                  >
                    {feat.desc}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* Latest Posts */}
      <ScrollReveal delay={100}>
        <section className="relative z-[1] pb-[100px] max-[600px]:pb-[60px]">
          <div className="mx-auto px-6" style={{ maxWidth: "1200px" }}>
            <div style={{ marginBottom: "60px" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "3px",
                  color: NEON_CYAN,
                  marginBottom: "12px",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "1px",
                    background: NEON_CYAN,
                    boxShadow: `0 0 8px ${NEON_CYAN}`,
                  }}
                />
                {t("posts.feedLabel")}
              </div>
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
                <span style={{ color: NEON_AMBER }}>
                  {t("posts.titleHighlight")}
                </span>
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
                {data.items[0] &&
                  (() => {
                    const tokens = data.items[0].design_tokens as
                      | { images?: { hero?: string } }
                      | null
                      | undefined;
                    const rawHero = tokens?.images?.hero ?? "";
                    const imageUrl = rawHero
                      ? toPublicCarouselImageUrl(rawHero)
                      : "";
                    return (
                      <Link
                        href={`/blog/${data.items[0].id}`}
                        className="transform rounded-xl overflow-hidden border border-[rgba(0,212,255,0.1)] bg-bg-surface flex flex-col no-underline text-inherit transition-all duration-300 min-w-0 hover:border-[rgba(0,212,255,0.2)] hover:shadow-[0_0_30px_rgba(0,212,255,0.03)] hover:-translate-y-1 active:-translate-y-1 motion-reduce:hover:translate-y-0 motion-reduce:active:translate-y-0"
                      >
                        <div
                          style={{
                            height: "220px",
                            background: `linear-gradient(135deg, rgba(0,212,255,0.08), rgba(255,39,112,0.04))`,
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            fontFamily:
                              "'JetBrains Mono', ui-monospace, monospace",
                            fontSize: "13px",
                            color: TEXT_DIM,
                            position: "relative",
                            overflow: "hidden",
                          }}
                        >
                          {imageUrl ? (
                            <Image
                              src={imageUrl}
                              alt=""
                              fill
                              className="object-cover"
                              sizes="(max-width: 768px) 100vw, 50vw"
                              unoptimized={
                                imageUrl.startsWith("http") ||
                                imageUrl.startsWith("/api/")
                              }
                            />
                          ) : (
                            <span>▸ carousel_preview.jpg</span>
                          )}
                          <div
                            style={{
                              position: "absolute",
                              inset: 0,
                              background: `linear-gradient(to top, ${BG_SURFACE} 0%, transparent 50%)`,
                            }}
                          />
                        </div>
                        <div
                          style={{
                            padding: "28px",
                            flex: 1,
                            display: "flex",
                            flexDirection: "column",
                          }}
                        >
                          <span
                            style={{
                              display: "inline-flex",
                              alignSelf: "flex-start",
                              padding: "3px 10px",
                              fontFamily:
                                "'JetBrains Mono', ui-monospace, monospace",
                              fontSize: "10px",
                              fontWeight: 700,
                              textTransform: "uppercase",
                              letterSpacing: "2px",
                              borderRadius: "3px",
                              color: NEON_MAGENTA,
                              background: "rgba(255,39,112,0.15)",
                              border: `1px solid rgba(255,39,112,0.15)`,
                              marginBottom: "12px",
                            }}
                          >
                            {data.items[0].niche || "Post"}
                          </span>
                          <h3
                            style={{
                              fontSize: "20px",
                              fontWeight: 800,
                              letterSpacing: "-0.02em",
                              marginBottom: "8px",
                            }}
                          >
                            {locale === "en"
                              ? data.items[0].title_en ||
                                data.items[0].title ||
                                data.items[0].topic
                              : data.items[0].title || data.items[0].topic}
                          </h3>
                          <p
                            style={{
                              fontSize: "14px",
                              color: TEXT_MUTED,
                              lineHeight: 1.7,
                              flex: 1,
                            }}
                          >
                            {truncateWords(
                              locale === "en"
                                ? data.items[0].subtitle_en ||
                                    data.items[0].subtitle ||
                                    data.items[0].topic
                                : data.items[0].subtitle || data.items[0].topic,
                              15,
                            )}
                          </p>
                          <span
                            style={{
                              fontFamily:
                                "'JetBrains Mono', ui-monospace, monospace",
                              fontSize: "11px",
                              color: TEXT_DIM,
                              marginTop: "16px",
                            }}
                          >
                            {new Date(
                              data.items[0].created_at,
                            ).toLocaleDateString("en-US", {
                              month: "short",
                              day: "numeric",
                              year: "numeric",
                            })}
                          </span>
                        </div>
                      </Link>
                    );
                  })()}

                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    gap: "12px",
                  }}
                >
                  {data.items.slice(1, 5).map((post) => (
                    <Link
                      key={post.id}
                      href={`/blog/${post.id}`}
                      className="rounded-lg border border-neon-card-border bg-bg-card p-5 no-underline text-inherit block transition-all duration-300 min-w-0 hover:border-white/10 hover:bg-bg-elevated"
                    >
                      <span
                        style={{
                          fontFamily:
                            "'JetBrains Mono', ui-monospace, monospace",
                          fontSize: "9px",
                          textTransform: "uppercase",
                          letterSpacing: "2px",
                          color: NEON_TEAL,
                          marginBottom: "6px",
                          display: "block",
                        }}
                      >
                        {post.niche || "Post"}
                      </span>
                      <h4
                        style={{
                          fontSize: "14px",
                          fontWeight: 600,
                          marginBottom: "4px",
                          lineHeight: 1.4,
                        }}
                      >
                        {locale === "en"
                          ? post.title_en || post.title || post.topic
                          : post.title || post.topic}
                      </h4>
                      <span
                        style={{
                          fontFamily:
                            "'JetBrains Mono', ui-monospace, monospace",
                          fontSize: "10px",
                          color: TEXT_DIM,
                        }}
                      >
                        {new Date(post.created_at).toLocaleDateString("en-US", {
                          month: "short",
                          day: "numeric",
                          year: "numeric",
                        })}
                      </span>
                    </Link>
                  ))}
                </div>
              </div>
            )}
          </div>
        </section>
      </ScrollReveal>

      {/* About Me */}
      <ScrollReveal delay={100}>
        <section className="relative z-[1] py-20 max-[600px]:py-0 max-[600px]:pb-[60px]">
          <div className="mx-auto px-6" style={{ maxWidth: "1200px" }}>
            <div style={{ marginBottom: "40px" }}>
              <div
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "8px",
                  fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                  fontSize: "11px",
                  fontWeight: 700,
                  textTransform: "uppercase",
                  letterSpacing: "3px",
                  color: NEON_CYAN,
                  marginBottom: "12px",
                }}
              >
                <span
                  style={{
                    width: "24px",
                    height: "1px",
                    background: NEON_CYAN,
                    boxShadow: `0 0 8px ${NEON_CYAN}`,
                  }}
                />
                {t("about.label")}
              </div>
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
                <span style={{ color: NEON_MAGENTA }}>
                  {t("about.titleHighlight")}
                </span>
              </h2>
            </div>

            <div className="grid grid-cols-2 gap-12 items-center min-w-0 max-[900px]:grid-cols-1">
              <div style={{ position: "relative" }}>
                <div
                  style={{
                    width: "100%",
                    aspectRatio: "3/4",
                    borderRadius: "12px",
                    background: `linear-gradient(135deg, rgba(0,212,255,0.08), rgba(255,39,112,0.04))`,
                    border: `1px solid rgba(0,212,255,0.1)`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    overflow: "hidden",
                  }}
                >
                  <Image
                    src="/about-pedro.jpg"
                    alt="Pedro Marins"
                    width={360}
                    height={480}
                    style={{
                      objectFit: "cover",
                      width: "100%",
                      height: "100%",
                    }}
                    unoptimized
                  />
                </div>
                <div
                  style={{
                    position: "absolute",
                    top: "-12px",
                    right: "-12px",
                    padding: "8px 16px",
                    borderRadius: "6px",
                    background: `rgba(0,212,255,0.1)`,
                    border: `1px solid rgba(0,212,255,0.2)`,
                    fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                    fontSize: "11px",
                    color: NEON_CYAN,
                    backdropFilter: "blur(8px)",
                  }}
                >
                  <span style={{ fontWeight: 700 }}>
                    {t("about.badgeYears")}
                  </span>{" "}
                  {t("about.badgeLabel")}
                </div>
              </div>
              <div>
                <h3
                  style={{
                    fontSize: "24px",
                    fontWeight: 700,
                    marginBottom: "16px",
                    letterSpacing: "-0.02em",
                  }}
                >
                  {t("about.greeting")}
                </h3>
                <p
                  style={{
                    fontSize: "15px",
                    color: TEXT_MUTED,
                    lineHeight: 1.8,
                    marginBottom: "16px",
                  }}
                >
                  {t("about.paragraph1")}
                </p>
                <p
                  style={{
                    fontSize: "15px",
                    color: TEXT_MUTED,
                    lineHeight: 1.8,
                    marginBottom: "16px",
                  }}
                >
                  {t("about.paragraph2")}
                </p>
                <p
                  style={{
                    fontSize: "15px",
                    color: TEXT_MUTED,
                    lineHeight: 1.8,
                    marginBottom: "24px",
                  }}
                >
                  {t("about.paragraph3")}
                </p>
                <p
                  style={{
                    fontSize: "15px",
                    color: TEXT_MUTED,
                    lineHeight: 1.8,
                    marginBottom: "24px",
                  }}
                >
                  {t("about.paragraph4")}
                </p>
                <div
                  style={{
                    display: "flex",
                    gap: "12px",
                    flexWrap: "wrap",
                    marginBottom: "24px",
                  }}
                >
                  {[
                    "Python",
                    "TypeScript",
                    "Angular",
                    "React",
                    "Node.js",
                    "LangChain",
                    "PostgreSQL",
                    "AWS",
                    "AI/ML",
                  ].map((skill) => (
                    <span
                      key={skill}
                      style={{
                        padding: "4px 12px",
                        borderRadius: "4px",
                        fontSize: "11px",
                        fontWeight: 600,
                        fontFamily: "'JetBrains Mono', ui-monospace, monospace",
                        color: NEON_TEAL,
                        background: "rgba(10,197,168,0.1)",
                        border: "1px solid rgba(10,197,168,0.15)",
                      }}
                    >
                      {skill}
                    </span>
                  ))}
                </div>
                {/* Social Links */}
                <div style={{ display: "flex", gap: "12px" }}>
                  {[
                    {
                      label: t("about.socialLinkedIn"),
                      href: "https://www.linkedin.com/in/pedro-marins-179971ba",
                    },
                    {
                      label: t("about.socialGitHub"),
                      href: "https://github.com/rickwalking",
                    },
                    {
                      label: t("about.socialInstagram"),
                      href: "https://www.instagram.com/pedromarins.ai",
                    },
                  ].map((link) => (
                    <a
                      key={link.label}
                      href={link.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 py-2 px-4 rounded-md text-[13px] font-semibold no-underline text-neon-cyan bg-[rgba(0,212,255,0.08)] border border-[rgba(0,212,255,0.15)] transition-all duration-[250ms] ease-[cubic-bezier(0.25,1,0.5,1)] hover:bg-neon-cyan-dim hover:border-neon-cyan hover:-translate-y-0.5 active:-translate-y-0.5 motion-reduce:hover:translate-y-0 motion-reduce:active:translate-y-0"
                    >
                      <svg
                        width="14"
                        height="14"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6" />
                        <polyline points="15 3 21 3 21 9" />
                        <line x1="10" y1="14" x2="21" y2="3" />
                      </svg>
                      {link.label}
                    </a>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </section>
      </ScrollReveal>

      {/* Footer */}
      <footer
        style={{
          position: "relative",
          zIndex: 1,
          borderTop: `1px solid rgba(0,212,255,0.06)`,
          padding: "40px 0",
          background: "rgba(6,10,18,0.5)",
        }}
      >
        <div
          className="mx-auto px-6"
          style={{
            maxWidth: "1200px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: "11px",
            color: TEXT_DIM,
          }}
        >
          <span>© 2026 Pedro Marins</span>
        </div>
      </footer>

      {/* Landing particle drift — distinct from globals.css particle-float used elsewhere */}
      <style>{`
        @keyframes particle-float-landing {
          0% { transform: translateY(0) translateX(0); opacity: 0; }
          10% { opacity: 1; }
          90% { opacity: 1; }
          100% { transform: translateY(-100vh) translateX(100px); opacity: 0; }
        }
      `}</style>
    </>
  );
}

export default async function HomePage() {
  const t = await getTranslations("home");
  const tc = await getTranslations("common");
  const tb = await getTranslations("blog");

  const cookieStore = await cookies();
  const localeCookie = cookieStore.get("locale")?.value;
  const locale: SupportedLocale =
    localeCookie && SUPPORTED_LOCALES.includes(localeCookie as SupportedLocale)
      ? (localeCookie as SupportedLocale)
      : DEFAULT_LOCALE;

  const data: CarouselProjectListResponse = await fetchCompletedProjects(5);
  const fallback = FALLBACK_DESIGN_TOKENS;

  return (
    <HomePageContent
      t={t}
      tc={tc}
      tb={tb}
      data={data}
      locale={locale}
      fallback={fallback}
    />
  );
}
