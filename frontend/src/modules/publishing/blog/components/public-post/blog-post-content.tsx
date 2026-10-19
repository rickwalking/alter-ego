import ReactMarkdown from "react-markdown";
import { isSafeMarkdownHref } from "@/lib/safe-markdown-href";
import { PublicCoverImage } from "./public-cover-image";
import type {
  BlogPostContentProps,
  SectionBodyProps,
  SectionHeadingProps,
  SectionProps,
} from "./types";

/**
 * Public renderer of a `blog.v2` document (AE-0423, ADR-0025): each section's
 * own heading, body and image with its stored alt. The title H1 belongs to the
 * page header, so no section renders an H1 (a stray `#` in a body becomes an
 * H2), and markdown images are not rendered: images come only from the
 * document (never a carousel slide). Bodies go through the react-markdown
 * allow-list + `isSafeMarkdownHref`; raw HTML is never rendered.
 */

const SECTION_IMAGE_SIZES = "(max-width: 768px) 100vw, 768px";

function SectionBody({ markdown, design }: SectionBodyProps) {
  const { colors, typography } = design;

  return (
    <ReactMarkdown
      allowedElements={[
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
      ]}
      components={{
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
          <li
            className="flex gap-3 text-base"
            style={{ color: colors.text_muted }}
          >
            <span
              className="shrink-0 text-lg"
              style={{ color: colors.primary }}
            >
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
      }}
    >
      {markdown}
    </ReactMarkdown>
  );
}

function SectionHeading({ heading, design }: SectionHeadingProps) {
  if (!heading) return null;
  return (
    <h2
      className="mt-10 mb-6 text-3xl font-extrabold leading-tight"
      style={{
        color: design.colors.text,
        fontFamily: design.typography.font_family_heading,
      }}
    >
      {heading}
    </h2>
  );
}

function Section({ heading, bodyMd, image, design }: SectionProps) {
  return (
    <section className="space-y-6">
      <SectionHeading heading={heading} design={design} />
      {image && (
        <PublicCoverImage
          src={image.url}
          alt={image.alt}
          sizes={SECTION_IMAGE_SIZES}
          frameClassName="relative h-64 w-full overflow-hidden rounded-xl md:h-80"
          frameStyle={{ border: `1px solid ${design.colors.primary}33` }}
        />
      )}
      <SectionBody markdown={bodyMd} design={design} />
    </section>
  );
}

export function BlogPostContent({ sections, design }: BlogPostContentProps) {
  return (
    <div className="space-y-6">
      {sections.map((section) => (
        <Section
          key={section.id}
          heading={section.heading}
          bodyMd={section.body_md}
          image={section.image}
          design={design}
        />
      ))}
    </div>
  );
}
