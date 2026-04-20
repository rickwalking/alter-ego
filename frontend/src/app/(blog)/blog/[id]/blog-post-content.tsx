import ReactMarkdown from "react-markdown";
import type { ReactNode } from "react";
import type { CarouselDesignResponse } from "@/schemas/carousel";

interface BlogPostContentProps {
  markdown: string;
  design: CarouselDesignResponse;
  slideImages: string[];
}

interface SectionProps {
  markdown: string;
  design: CarouselDesignResponse;
  slideImage: string | null;
}

function Section({ markdown, design, slideImage }: SectionProps) {
  const { colors, typography } = design;

  return (
    <>
      <ReactMarkdown
        components={{
          h1: ({ children }) => (
            <h1
              className="mb-6 text-4xl font-extrabold leading-tight"
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
            <p className="text-base leading-relaxed" style={{ color: colors.text_muted }}>
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
      {slideImage && (
        <div
          className="mb-8 overflow-hidden rounded-2xl"
          style={{
            border: `1px solid ${colors.primary}1F`,
            boxShadow: `0 0 30px ${colors.primary}0D`,
          }}
        >
          <img
            src={slideImage}
            alt=""
            className="h-auto w-full object-cover"
            loading="lazy"
          />
        </div>
      )}
    </>
  );
}

export function BlogPostContent({ markdown, design, slideImages }: BlogPostContentProps) {
  const sections = splitByH2(markdown);
  const contentSlides = slideImages.length > 1 ? slideImages.slice(1) : [];

  return (
    <div className="space-y-6">
      {sections.map((section, index) => {
        const slideImage = index > 0 && index - 1 < contentSlides.length
          ? contentSlides[index - 1]
          : null;

        return (
          <Section
            key={index}
            markdown={section}
            design={design}
            slideImage={slideImage}
          />
        );
      })}
    </div>
  );
}

function splitByH2(markdown: string): string[] {
  const H2_SEPARATOR = "\n## ";
  const parts = markdown.split(H2_SEPARATOR);

  if (parts.length <= 1) {
    return [markdown];
  }

  const sections: string[] = [parts[0]];
  for (let i = 1; i < parts.length; i++) {
    sections.push("## " + parts[i]);
  }

  return sections;
}

function extractTextFromChildren(children: ReactNode): string {
  if (typeof children === "string") return children;
  if (Array.isArray(children)) return children.map(extractTextFromChildren).join(" ");
  if (children && typeof children === "object" && "props" in (children as object)) {
    return extractTextFromChildren(
      (children as { props: { children: ReactNode } }).props.children
    );
  }
  return "";
}