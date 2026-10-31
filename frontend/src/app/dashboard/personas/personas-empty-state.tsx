"use client";

import { UserRound } from "lucide-react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TEXT, TEXT_MUTED } from "@/constants/neon";

/** Empty-state illustration size (px). */
const EMPTY_ICON_SIZE = 56;

export interface PersonasEmptyStateProps {
  searchQuery: string;
  onCreate: () => void;
}

/** No personas yet (with the create action), or no match for the search. */
export function PersonasEmptyState({
  searchQuery,
  onCreate,
}: Readonly<PersonasEmptyStateProps>): React.ReactElement {
  const t = useTranslations("personas.empty");
  const searching = searchQuery.length > 0;
  return (
    <div
      className="flex flex-col items-center justify-center px-5 py-16 text-center sm:py-20"
      style={{ color: TEXT_MUTED }}
    >
      <UserRound
        size={EMPTY_ICON_SIZE}
        className="mb-4 opacity-40"
        aria-hidden="true"
      />
      <h3 className="mb-2 text-lg font-bold" style={{ color: TEXT }}>
        {searching ? t("title") : t("firstTitle")}
      </h3>
      <p className="m-0 max-w-[400px] text-sm leading-relaxed">
        {searching ? t("noResults", { query: searchQuery }) : t("body")}
      </p>
      {!searching && (
        <NeonButton
          variant="primary"
          size="md"
          className="mt-6 min-h-11"
          onClick={onCreate}
        >
          {t("action")}
        </NeonButton>
      )}
    </div>
  );
}
