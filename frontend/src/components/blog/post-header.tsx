import type { CarouselDesignResponse } from "@/schemas/carousel";

interface PostHeaderProps {
  title: string;
  subtitle?: string;
  date?: string;
  readTime?: string;
  badge: string;
  design: CarouselDesignResponse;
}

export function PostHeader({ title, subtitle, date, readTime, badge, design }: PostHeaderProps) {
  const { colors, typography } = design;

  return (
    <>
      <div
        className="mb-6 inline-flex items-center gap-2 rounded-md border px-4 py-2 font-mono text-xs font-bold uppercase tracking-widest"
        style={{
          borderColor: `${colors.primary}4D`,
          background: `${colors.primary}14`,
          color: colors.primary,
          fontFamily: typography.font_family_badge,
        }}
      >
        {badge}
      </div>
      <h1
        className="mb-3 text-5xl font-extrabold leading-tight md:text-6xl"
        style={{ color: colors.text, fontFamily: typography.font_family_heading }}
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
      {(date || readTime) && (
        <div
          className="mb-8 flex items-center gap-4 border-b pb-6"
          style={{ borderColor: `${colors.primary}0F` }}
        >
          {date && (
            <span
              className="flex items-center gap-1 text-sm"
              style={{ color: "rgba(255,255,255,0.45)" }}
            >
              {new Date(date).toLocaleDateString("en-US", {
                month: "long",
                day: "numeric",
                year: "numeric",
              })}
            </span>
          )}
          {readTime && (
            <span
              className="flex items-center gap-1 text-sm"
              style={{ color: "rgba(255,255,255,0.45)" }}
            >
              {readTime}
            </span>
          )}
        </div>
      )}
    </>
  );
}
