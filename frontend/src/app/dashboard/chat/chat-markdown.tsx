import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import { isSafeMarkdownHref } from "@/lib/safe-markdown-href";
import {
  DASHBOARD_CHAT_BG_DEEP,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_MONO_FONT,
  DASHBOARD_CHAT_TEXT,
} from "@/modules/editorial-operations";

/** Elements an assistant reply may render; no images, no raw HTML. */
export const CHAT_MARKDOWN_ALLOWED_ELEMENTS = [
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
];

/** Links leave the site in a new tab and pass no referrer or ranking. */
export const CHAT_LINK_REL = "noopener noreferrer nofollow";

const HEADING_STYLE: React.CSSProperties = {
  margin: "12px 0 6px",
  fontSize: "14px",
  fontWeight: 700,
  color: DASHBOARD_CHAT_TEXT,
};

function Heading({ children }: Readonly<{ children?: React.ReactNode }>) {
  return <p style={HEADING_STYLE}>{children}</p>;
}

/** Whether a link still has visible content (an image inside it is dropped). */
function hasText(children: React.ReactNode): boolean {
  if (children === null || children === undefined || children === false) {
    return false;
  }
  if (Array.isArray(children)) {
    return children.some((child: React.ReactNode) => hasText(child));
  }
  return typeof children !== "string" || children.trim().length > 0;
}

const CHAT_MARKDOWN_COMPONENTS: Components = {
  h1: Heading,
  h2: Heading,
  h3: Heading,
  h4: Heading,
  h5: Heading,
  h6: Heading,
  p: ({ children }) => <p style={{ margin: "0 0 8px" }}>{children}</p>,
  strong: ({ children }) => (
    <strong style={{ color: DASHBOARD_CHAT_TEXT }}>{children}</strong>
  ),
  ul: ({ children }) => (
    <ul style={{ margin: "0 0 8px", paddingLeft: "20px", listStyle: "disc" }}>
      {children}
    </ul>
  ),
  ol: ({ children }) => (
    <ol
      style={{ margin: "0 0 8px", paddingLeft: "20px", listStyle: "decimal" }}
    >
      {children}
    </ol>
  ),
  blockquote: ({ children }) => (
    <blockquote
      style={{
        margin: "0 0 8px",
        paddingLeft: "10px",
        borderLeft: `2px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
      }}
    >
      {children}
    </blockquote>
  ),
  pre: ({ children }) => (
    <pre
      style={{
        margin: "0 0 8px",
        padding: "10px 12px",
        borderRadius: "6px",
        overflowX: "auto",
        whiteSpace: "pre",
        background: DASHBOARD_CHAT_BG_DEEP,
        border: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
      }}
    >
      {children}
    </pre>
  ),
  code: ({ children }) => (
    <code style={{ fontFamily: DASHBOARD_CHAT_MONO_FONT, fontSize: "12px" }}>
      {children}
    </code>
  ),
  a: ({ children, href }) => {
    if (!isSafeMarkdownHref(href)) {
      return <span>{children}</span>;
    }
    const label = hasText(children) ? children : href;
    return (
      <a
        href={href}
        target="_blank"
        rel={CHAT_LINK_REL}
        style={{ color: DASHBOARD_CHAT_CYAN, textDecoration: "underline" }}
      >
        {label}
      </a>
    );
  },
};

/**
 * An assistant reply rendered as markdown, safely: raw HTML is dropped, only
 * text-formatting elements are allowed (no images), and only http(s), mailto
 * and same-site links become clickable.
 */
export function ChatMarkdown({
  text,
}: Readonly<{ text: string }>): React.ReactElement {
  return (
    <div className="chat-markdown">
      <ReactMarkdown
        skipHtml
        allowedElements={CHAT_MARKDOWN_ALLOWED_ELEMENTS}
        unwrapDisallowed
        components={CHAT_MARKDOWN_COMPONENTS}
      >
        {text}
      </ReactMarkdown>
    </div>
  );
}
