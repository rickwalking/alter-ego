import ReactMarkdown from "react-markdown";
import type { CarouselDesignResponse } from "@/schemas/carousel";

interface PostContentProps {
  markdown: string;
  design: CarouselDesignResponse;
}

export function PostContent({ markdown, design }: PostContentProps) {
  const { colors, typography } = design;

  return (
    <div className="space-y-6">
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1
              className="mt-10 mb-6 text-4xl font-extrabold leading-tight"
              style={{ color: colors.text, fontFamily: typography.font_family_heading }}
            >
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2
              className="mt-10 mb-6 text-3xl font-extrabold leading-tight"
              style={{ color: colors.text, fontFamily: typography.font_family_heading }}
            >
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3
              className="mt-8 mb-4 text-2xl font-bold leading-tight"
              style={{ color: colors.text, fontFamily: typography.font_family_heading }}
            >
              {children}
            </h3>
          ),
          p: ({ children }) => (
            <p
              className="text-base leading-relaxed"
              style={{ color: colors.text_muted }}
            >
              {children}
            </p>
          ),
          strong: ({ children }) => (
            <strong style={{ color: colors.text }}>{children}</strong>
          ),
          em: ({ children }) => (
            <em style={{ color: colors.text_dim }}>{children}</em>
          ),
          code: ({ children }) => (
            <code
              className="rounded px-1.5 py-0.5 text-sm"
              style={{
                fontFamily: typography.font_family_badge,
                background: `${colors.primary}14`,
                color: colors.primary,
              }}
            >
              {children}
            </code>
          ),
          pre: ({ children }) => (
            <pre
              className="overflow-x-auto rounded-xl p-5"
              style={{
                background: `${colors.primary}0A`,
                border: `1px solid ${colors.primary}1F`,
                color: colors.text_muted,
              }}
            >
              {children}
            </pre>
          ),
          ul: ({ children }) => (
            <ul className="space-y-3">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="space-y-3 pl-6">{children}</ol>
          ),
          li: ({ children }) => (
            <li
              className="flex gap-3 text-base"
              style={{ color: colors.text_muted }}
            >
              <span className="shrink-0 text-lg" style={{ color: colors.primary }}>
                &bull;
              </span>
              <span>{children}</span>
            </li>
          ),
          blockquote: ({ children }) => (
            <blockquote
              className="rounded-l-lg border-l-4 p-5"
              style={{
                borderColor: design.colors.accent,
                background: `${design.colors.accent}08`,
              }}
            >
              <div
                className="mb-2 text-lg italic leading-relaxed"
                style={{ color: "rgba(255,255,255,0.58)" }}
              >
                {children}
              </div>
            </blockquote>
          ),
          a: ({ children, href }) => (
            <a
              href={href}
              target="_blank"
              rel="noopener noreferrer"
              className="underline transition-colors hover:opacity-80"
              style={{ color: colors.primary }}
            >
              {children}
            </a>
          ),
          hr: () => (
            <hr style={{ borderColor: `${colors.primary}1F` }} />
          ),
        }}
      >
        {markdown}
      </ReactMarkdown>
    </div>
  );
}