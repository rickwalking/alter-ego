"use client";

import { useLocale, useTranslations } from "next-intl";
import { formatLocaleDateTime } from "@/lib/locale-format";
import { DISTRIBUTION_FIELDS } from "@/modules/publishing/distribution/lib/copy-editor-state";
import type { CopyVersionEntriesProps, CopyVersionListProps } from "./types";

const NO_TEXTS: Readonly<Record<string, string>> = {};

const LANGUAGE_BY_FIELD: Readonly<Record<string, string>> = {
  [DISTRIBUTION_FIELDS.LINKEDIN_PT]: "PT",
  [DISTRIBUTION_FIELDS.LINKEDIN_EN]: "EN",
};

/**
 * "Histórico" under a caption / LinkedIn editor: every version of its texts,
 * newest first (a page at a time), with who wrote it and when, and "Restaurar"
 * on every version whose text is not the current saved one.
 * A restore waits while the text has unsaved edits. Without a history (a
 * read-only panel) nothing is shown.
 */
export function CopyVersionList(
  props: Readonly<CopyVersionListProps>,
): React.ReactElement | null {
  const { history, current = NO_TEXTS } = props;
  return history ? (
    <CopyVersionEntries {...props} history={history} current={current} />
  ) : null;
}

/** The list itself, once there is a history to show. */
function CopyVersionEntries({
  history,
  fields,
  blocked,
  current,
}: Readonly<CopyVersionEntriesProps>): React.ReactElement {
  const t = useTranslations("publish.copy.history");
  const tPublish = useTranslations("publish");
  const locale = useLocale();
  const versions = history.versions.filter((v) => fields.includes(v.field));
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
                <span>{version.author_name ?? t("previous")}</span>
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
              {restore && current[version.field] !== version.text && (
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
      {history.hasMore && (
        <button
          type="button"
          onClick={history.loadMore}
          className="rounded-md border border-[var(--color-border)] px-2 py-1 text-xs"
        >
          {t("loadMore")}
        </button>
      )}
    </section>
  );
}
