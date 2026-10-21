import type { Components } from "react-markdown";
import { isSafeMarkdownHref } from "@/lib/safe-markdown-href";
import type { CarouselDesignResponse } from "@/schemas/carousel";

/**
 * react-markdown allow-list + themed renderers for a public section body.
 * `h1` renders as an H2 (the page header owns the only H1) and
 * `img` is not allowed: section images come from the document, never markdown.
 */

export const SECTION_ALLOWED_ELEMENTS = [
  "h1",
  "h2",
  "h3",
  "h4",
  "h5",
  "h6",
  "p",
  "strong",
  "em",
  "code",
  "pre",
  "ul",
  "ol",
  "li",
  "blockquote",
  "a",
  "hr",
  "br",
  "table",
  "thead",
  "tbody",
  "tr",
  "th",
  "td",
  "del",
  "ins",
];

export function sectionMarkdownComponents(
  design: CarouselDesignResponse,
): Components {
  const { colors, typography } = design;
  return {
    h1: ({ children }) => (
      <h2
        className="mt-10 mb-6 text-3xl font-extrabold leading-tight"
        style={{
          color: colors.text,
          fontFamily: typography.font_family_heading,
        }}
      >
        {children}
      </h2>
    ),
    h2: ({ children }) => (
      <h2
        className="mt-10 mb-6 text-3xl font-extrabold leading-tight"
        style={{
          color: colors.text,
          fontFamily: typography.font_family_heading,
        }}
      >
        {children}
      </h2>
    ),
    h3: ({ children }) => (
      <h3
        className="mt-8 mb-4 text-2xl font-bold leading-tight"
        style={{
          color: colors.text,
          fontFamily: typography.font_family_heading,
        }}
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
    ul: ({ children }) => <ul className="space-y-3">{children}</ul>,
    ol: ({ children }) => <ol className="space-y-3 pl-6">{children}</ol>,
    li: ({ children }) => (
      <li className="flex gap-3 text-base" style={{ color: colors.text_muted }}>
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
          borderColor: colors.accent,
          background: `${colors.accent}08`,
        }}
      >
        <div className="mb-2 text-lg italic leading-relaxed text-muted-foreground/60">
          {children}
        </div>
      </blockquote>
    ),
    a: ({ children, href }) => {
      if (!isSafeMarkdownHref(href)) {
        return (
          <span
            className="underline decoration-dotted"
            style={{ color: colors.text_muted }}
          >
            {children}
          </span>
        );
      }
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="underline transition-colors hover:opacity-80"
          style={{ color: colors.primary }}
        >
          {children}
        </a>
      );
    },
    hr: () => <hr style={{ borderColor: `${colors.primary}1F` }} />,
  };
}
