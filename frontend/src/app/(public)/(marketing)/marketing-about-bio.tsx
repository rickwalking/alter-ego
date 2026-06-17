import Image from "next/image";
import { NEON_CYAN, NEON_TEAL, TEXT_MUTED } from "@/constants/neon";
import type { MarketingAboutProps } from "@/app/(public)/(marketing)/types";

const ABOUT_SKILLS = [
  "Python",
  "TypeScript",
  "Angular",
  "React",
  "Node.js",
  "LangChain",
  "PostgreSQL",
  "AWS",
  "AI/ML",
];

const ABOUT_PARAGRAPH_BASE = {
  fontSize: "15px",
  color: TEXT_MUTED,
  lineHeight: 1.8,
} as const;

function AboutSocialLinks({ t }: MarketingAboutProps): React.ReactElement {
  const links = [
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
  ];
  return (
    <div style={{ display: "flex", gap: "12px" }}>
      {links.map((link) => (
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
  );
}

export function AboutPortrait({ t }: MarketingAboutProps): React.ReactElement {
  return (
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
          style={{ objectFit: "cover", width: "100%", height: "100%" }}
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
        <span style={{ fontWeight: 700 }}>{t("about.badgeYears")}</span>{" "}
        {t("about.badgeLabel")}
      </div>
    </div>
  );
}

export function AboutBio({ t }: MarketingAboutProps): React.ReactElement {
  return (
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
      <p style={{ ...ABOUT_PARAGRAPH_BASE, marginBottom: "16px" }}>
        {t("about.paragraph1")}
      </p>
      <p style={{ ...ABOUT_PARAGRAPH_BASE, marginBottom: "16px" }}>
        {t("about.paragraph2")}
      </p>
      <p style={{ ...ABOUT_PARAGRAPH_BASE, marginBottom: "24px" }}>
        {t("about.paragraph3")}
      </p>
      <p style={{ ...ABOUT_PARAGRAPH_BASE, marginBottom: "24px" }}>
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
        {ABOUT_SKILLS.map((skill) => (
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
      <AboutSocialLinks t={t} />
    </div>
  );
}
