import ReactMarkdown from "react-markdown";
import { PublicCoverImage } from "./public-cover-image";
import {
  SECTION_ALLOWED_ELEMENTS,
  sectionMarkdownComponents,
} from "./section-markdown-components";
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
  return (
    <ReactMarkdown
      allowedElements={SECTION_ALLOWED_ELEMENTS}
      components={sectionMarkdownComponents(design)}
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
