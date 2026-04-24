import type { CarouselDesignResponse } from "@/schemas/carousel";

interface BlogPostHeaderProps {
  title: string;
  subtitle?: string;
  badge: string;
  design: CarouselDesignResponse;
  currentLang: string;
  availableLanguages: string[];
  blogPath: string;
}

export function BlogPostHeader({
  title,
  subtitle,
  badge,
  design,
  currentLang,
  availableLanguages,
  blogPath,
}: BlogPostHeaderProps) {
  const { colors, typography } = design;

  return (
    <>
      <div className="mb-6 flex items-center gap-3">
        <div
          className="inline-flex items-center gap-2 rounded-md border px-4 py-2 font-mono text-xs font-bold uppercase tracking-widest"
          style={{
            borderColor: `${colors.primary}4D`,
            background: `${colors.primary}14`,
            color: colors.primary,
            fontFamily: typography.font_family_badge,
          }}
        >
          {badge}
        </div>
        {availableLanguages.length > 1 && (
          <div className="flex items-center gap-1">
            {availableLanguages.map((lang) => (
              <a
                key={lang}
                href={`${blogPath}${blogPath.includes("?") ? "&" : "?"}lang=${lang}`}
                className="rounded px-2.5 py-1 text-xs font-bold uppercase tracking-wide transition-all"
                style={
                  lang === currentLang
                    ? {
                        background: `${colors.primary}29`,
                        color: colors.primary,
                        border: `1px solid ${colors.primary}4D`,
                      }
                    : {
                        color: colors.text_dim,
                        border: `1px solid ${colors.border}`,
                      }
                }
              >
                {lang === "pt" ? "🇧🇷 PT" : "🇺🇸 EN"}
              </a>
            ))}
          </div>
        )}
      </div>
      <h1
        className="mb-3 text-5xl font-extrabold leading-tight md:text-6xl"
        style={{ color: colors.text }}
      >
        {title}
      </h1>
      {subtitle && (
        <p
          className="mb-6 text-2xl leading-relaxed"
          style={{ color: colors.text_dim }}
        >
          {subtitle}
        </p>
      )}
      <div
        className="mb-8 border-b pb-6"
        style={{ borderColor: `${colors.primary}0F` }}
      >
        <span
          className="flex items-center gap-1 text-sm"
          style={{ color: "rgba(255,255,255,0.45)" }}
        >
          {design.layout.swipe_text}
        </span>
      </div>
    </>
  );
}
