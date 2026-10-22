"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";

export interface PersonasEmptyStateProps {
  searchQuery: string;
  onCreate: () => void;
}

/** No personas (with a create action), or no match for the search. */
export function PersonasEmptyState({
  searchQuery,
  onCreate,
}: Readonly<PersonasEmptyStateProps>): React.ReactElement {
  const t = useTranslations("personas.empty");
  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "80px 20px",
        textAlign: "center",
        color: "rgba(255,255,255,0.55)",
      }}
    >
      <svg
        width="56"
        height="56"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        style={{ opacity: 0.2, marginBottom: 16 }}
        aria-hidden="true"
      >
        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
        <circle cx="12" cy="7" r="4" />
      </svg>
      <h3
        style={{
          fontSize: 18,
          color: "rgba(255,255,255,0.45)",
          marginBottom: 8,
          fontWeight: 700,
        }}
      >
        {t("title")}
      </h3>
      <p style={{ fontSize: 13, maxWidth: 400, lineHeight: 1.6, margin: 0 }}>
        {searchQuery ? t("noResults", { query: searchQuery }) : t("body")}
      </p>
      {!searchQuery && (
        <NeonButton
          variant="primary"
          size="sm"
          className="mt-4"
          onClick={onCreate}
        >
          {t("action")}
        </NeonButton>
      )}
    </div>
  );
}
