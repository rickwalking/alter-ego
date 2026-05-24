import ReactMarkdown from "react-markdown";
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
          "img",
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
            <h1
              className="mb-6 text-4xl font-extrabold leading-tight"
              style={{
                color: colors.text,
                fontFamily: typography.font_family_heading,
              }}
            >
              {children}
            </h1>
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
          hr: () => <hr style={{ borderColor: `${colors.primary}1F` }} />,
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
            className="h-auto w-full object-cover" />
        </div>
      )}
    </>
  );
}

export function extractH2Heading(markdown: string): string | null {
  const match = markdown.match(/^##\s+(.+)$/m);
  return match ? match[1].trim() : null;
}

export function resolveSlideImage(
  sectionMarkdown: string,
  design: CarouselDesignResponse,
  slideImages: string[],
  sectionIndex: number,
): string | null {
  const heading = extractH2Heading(sectionMarkdown);
  if (!heading) {
    return null;
  }

  const imageMap = design.images.blog_image_map;
  if (imageMap && imageMap.length > 0) {
    const entry = imageMap.find((e) => e.heading.trim() === heading);
    if (
      entry &&
      entry.slide_number >= 1 &&
      entry.slide_number <= slideImages.length
    ) {
      return slideImages[entry.slide_number - 1];
    }
    return null;
  }

  // Fallback: positional mapping for legacy posts without image map.
  // Skip the first section (intro) and map each H2 section to a content slide.
  if (sectionIndex > 0) {
    const contentSlides = slideImages.length > 1 ? slideImages.slice(1) : [];
    const slideIndex = sectionIndex - 1;
    if (slideIndex < contentSlides.length) {
      return contentSlides[slideIndex];
    }
  }
  return null;
}

function stripLeadingH1(markdown: string): string {
  const lines = markdown.split("\n");
  if (lines.length === 0) return markdown;
  const first = lines[0].trim();
  if (first.startsWith("# ")) {
    let idx = 1;
    while (idx < lines.length && lines[idx].trim() === "") {
      idx += 1;
    }
    return lines.slice(idx).join("\n");
  }
  return markdown;
}

export function BlogPostContent({
  markdown,
  design,
  slideImages,
}: BlogPostContentProps) {
  const cleaned = stripLeadingH1(markdown);
  const sections = splitByH2(cleaned);

  return (
    <div className="space-y-6">
      {sections.map((section, index) => {
        const slideImage =
          index === 0
            ? null
            : resolveSlideImage(section, design, slideImages, index);

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
