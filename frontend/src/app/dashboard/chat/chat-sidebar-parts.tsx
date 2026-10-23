import {
  DASHBOARD_CHAT_BG_INPUT_DARK,
  DASHBOARD_CHAT_BORDER_LIGHT,
  DASHBOARD_CHAT_BORDER_SUBTLE,
  DASHBOARD_CHAT_TEXT,
  DASHBOARD_CHAT_TEXT_DIM,
} from "@/modules/editorial-operations";

/** The sidebar's search box (the parent owns the text and the matching). */
export function ChatSidebarSearch({
  query,
  onQueryChange,
  label,
  placeholder,
}: Readonly<{
  query: string;
  onQueryChange?: (query: string) => void;
  label: string;
  placeholder: string;
}>): React.ReactElement {
  return (
    <div
      style={{
        padding: "16px",
        borderBottom: `1px solid ${DASHBOARD_CHAT_BORDER_SUBTLE}`,
      }}
    >
      <input
        type="search"
        value={query}
        onChange={(event) => onQueryChange?.(event.target.value)}
        aria-label={label}
        placeholder={placeholder}
        style={{
          width: "100%",
          padding: "8px 12px",
          borderRadius: "6px",
          border: `1px solid ${DASHBOARD_CHAT_BORDER_LIGHT}`,
          background: DASHBOARD_CHAT_BG_INPUT_DARK,
          color: DASHBOARD_CHAT_TEXT,
          fontSize: "13px",
          fontFamily: "inherit",
          outline: "none",
        }}
      />
    </div>
  );
}

/** Says no conversation matches the search (only once the search is done). */
export function ChatSidebarNoMatches({
  show,
  label,
}: Readonly<{ show: boolean; label: string }>): React.ReactElement | null {
  if (!show) return null;
  return (
    <p
      style={{
        padding: "10px 12px",
        fontSize: "12px",
        color: DASHBOARD_CHAT_TEXT_DIM,
      }}
    >
      {label}
    </p>
  );
}

/** Loads the next page of conversations; hidden when there is none. */
export function ChatSidebarMore({
  onLoadMore,
  label,
}: Readonly<{
  onLoadMore?: () => void;
  label: string;
}>): React.ReactElement | null {
  if (!onLoadMore) return null;
  return (
    <button
      type="button"
      onClick={onLoadMore}
      className="min-h-11 w-full rounded-md"
      style={{
        marginTop: "8px",
        border: `1px solid ${DASHBOARD_CHAT_BORDER_LIGHT}`,
        background: "transparent",
        color: DASHBOARD_CHAT_TEXT,
        fontSize: "12px",
        cursor: "pointer",
      }}
    >
      {label}
    </button>
  );
}
