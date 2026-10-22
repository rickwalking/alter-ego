"use client";

import { useLocale, useTranslations } from "next-intl";
import { formatLocaleDateTime } from "@/lib/locale-format";
import type { CopyVersionView } from "@/modules/publishing/distribution/hooks/types";
import type { CopyVersionEntriesProps, CopyVersionListProps } from "./types";

const LANGUAGE_BY_FIELD: Readonly<Record<string, string>> = {
  linkedin_post_pt: "PT",
  linkedin_post_en: "EN",
};

/** The newest version of each field: it is the current text, nothing to restore. */
function currentVersionNumbers(
  versions: readonly CopyVersionView[],
): Set<number> {
  const seen = new Set<string>();
  const current = new Set<number>();
  for (const version of versions) {
    if (!seen.has(version.field)) {
      seen.add(version.field);
      current.add(version.version_number);
    }
  }
  return current;
}

/**
 * "Histórico" under a caption / LinkedIn editor: every version of its texts,
 * newest first, with who wrote it and when, and "Restaurar" on older ones.
 * A restore waits while the text has unsaved edits. Without a history (a
 * read-only panel) nothing is shown.
 */
export function CopyVersionList(
  props: Readonly<CopyVersionListProps>,
): React.ReactElement | null {
  const { history } = props;
  return history ? <CopyVersionEntries {...props} history={history} /> : null;
}

/** The list itself, once there is a history to show. */
function CopyVersionEntries({
  history,
  fields,
  blocked,
}: Readonly<CopyVersionEntriesProps>): React.ReactElement {
  const t = useTranslations("publish.copy.history");
  const tPublish = useTranslations("publish");
  const locale = useLocale();
  const versions = history.versions.filter((v) => fields.includes(v.field));
  const current = currentVersionNumbers(versions);
  const { status, restore } = history;
  return (
    <section aria-label={t("title")} className="space-y-2">
      <h3 className="font-medium text-sm">{t("title")}</h3>
      {status.kind === "error" && (
        <p role="alert" className="text-destructive text-xs">
          {tPublish(status.errorKey)}
        </p>
      )}
      {blocked && versions.length > 0 && (
        <p className="text-[var(--color-text-muted)] text-xs">{t("blocked")}</p>
      )}
      {versions.length === 0 ? (
        <p className="text-[var(--color-text-muted)] text-xs">
          {history.loading ? t("loading") : t("empty")}
        </p>
      ) : (
        <ol className="max-h-64 space-y-2 overflow-auto">
          {versions.map((version) => (
            <li
              key={version.version_number}
              className="space-y-1 rounded-md border border-[var(--color-border)] p-2 text-xs"
            >
              <div className="flex flex-wrap items-center gap-2 text-[var(--color-text-muted)]">
                <span className="font-medium text-[var(--color-text)]">
                  {t("version", { number: version.version_number })}
                </span>
                {LANGUAGE_BY_FIELD[version.field] && (
                  <span>{LANGUAGE_BY_FIELD[version.field]}</span>
                )}
                <span>{version.author_name ?? t("generated")}</span>
                <time dateTime={version.created_at}>
                  {formatLocaleDateTime(version.created_at, locale)}
                </time>
                {version.restored_from ? (
                  <span>
                    {t("restoredFrom", { number: version.restored_from })}
                  </span>
                ) : null}
              </div>
              <p className="line-clamp-3 whitespace-pre-wrap">{version.text}</p>
              {restore && !current.has(version.version_number) && (
                <button
                  type="button"
                  disabled={blocked || status.kind === "restoring"}
                  onClick={() => {
                    void restore(version.version_number);
                  }}
                  aria-label={t("restoreVersion", {
                    number: version.version_number,
                  })}
                  className="rounded-md border border-[var(--color-border)] px-2 py-1 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {status.kind === "restoring" &&
                  status.versionNumber === version.version_number
                    ? t("restoring")
                    : t("restore")}
                </button>
              )}
            </li>
          ))}
        </ol>
      )}
    </section>
  );
}
