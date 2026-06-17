/**
 * Loading fallback for the document list (ADR-010 Suspense pattern).
 *
 * Extracted verbatim from the former `DocumentList` `isLoading` branch so the
 * `<Suspense fallback>` renders an identical skeleton — the loading UX is
 * unchanged by the migration.
 */
export function DocumentListSkeleton(): React.ReactElement {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
      {[1, 2, 3].map((i) => (
        <div
          key={i}
          className="h-40 animate-pulse rounded-lg bg-[var(--color-muted)]"
        />
      ))}
    </div>
  );
}
