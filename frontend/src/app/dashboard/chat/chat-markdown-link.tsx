import {
  isSafeMarkdownHref,
  normalizeMarkdownHref,
} from "@/lib/safe-markdown-href";
import {
  DASHBOARD_CHAT_CYAN,
  DASHBOARD_CHAT_TEXT_DIM,
} from "@/modules/editorial-operations";

/** External links leave the site in a new tab and pass no referrer or ranking. */
export const CHAT_LINK_REL = "noopener noreferrer nofollow";

/** Schemes that leave the site; same-site paths and anchors stay in the tab. */
const EXTERNAL_LINK = /^(?:https?|mailto):/i;
const WEB_LINK = /^https?:/i;

const LINK_STYLE: React.CSSProperties = {
  color: DASHBOARD_CHAT_CYAN,
  textDecoration: "underline",
};

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

/** The label's text when it is plain text (an autolink's label is its URL). */
function labelText(children: React.ReactNode): string {
  if (typeof children === "string") return children;
  if (!Array.isArray(children)) return "";
  return children.every((child) => typeof child === "string")
    ? children.join("")
    : "";
}

/** The host of a web link, shown beside it unless the label already names it. */
function visibleHost(href: string, label: string): string | null {
  if (!WEB_LINK.test(href)) return null;
  const { host } = new URL(href);
  return label.includes(host) ? null : host;
}

/**
 * A link in an assistant reply. Unsafe targets stay plain text; external
 * links open in a new tab and show their host, so a link to another site is
 * visible before the click; same-site links stay in the tab.
 */
export function ChatMarkdownLink({
  children,
  href,
}: Readonly<{
  children?: React.ReactNode;
  href?: string;
}>): React.ReactElement {
  const target = href === undefined ? undefined : normalizeMarkdownHref(href);
  const labelIsHref = !hasText(children);
  const label = labelIsHref ? target : children;
  if (target === undefined || !isSafeMarkdownHref(target)) {
    return <span>{label}</span>;
  }
  if (!EXTERNAL_LINK.test(target)) {
    return (
      <a href={target} style={LINK_STYLE}>
        {label}
      </a>
    );
  }
  const host = visibleHost(target, labelIsHref ? target : labelText(children));
  return (
    <>
      <a href={target} target="_blank" rel={CHAT_LINK_REL} style={LINK_STYLE}>
        {label}
      </a>
      {host && (
        <span style={{ color: DASHBOARD_CHAT_TEXT_DIM }}>{` (${host})`}</span>
      )}
    </>
  );
}
