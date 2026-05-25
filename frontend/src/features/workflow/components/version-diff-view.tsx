"use client";

type VersionDiffViewProps = {
  leftLabel: string;
  rightLabel: string;
  leftText: string;
  rightText: string;
};

function computeLineDiff(
  left: string,
  right: string,
): Array<{ type: "same" | "removed" | "added"; line: string }> {
  const leftLines = left.split("\n");
  const rightLines = right.split("\n");
  const maxLen = Math.max(leftLines.length, rightLines.length);
  const result: Array<{ type: "same" | "removed" | "added"; line: string }> =
    [];

  for (let i = 0; i < maxLen; i += 1) {
    const l = leftLines[i];
    const r = rightLines[i];
    if (l === r) {
      if (l !== undefined) result.push({ type: "same", line: l });
    } else {
      if (l !== undefined) result.push({ type: "removed", line: l });
      if (r !== undefined) result.push({ type: "added", line: r });
    }
  }
  return result;
}

export function VersionDiffView({
  leftLabel,
  rightLabel,
  leftText,
  rightText,
}: VersionDiffViewProps) {
  const diff = computeLineDiff(leftText, rightText);

  return (
    <div className="space-y-2">
      <div className="flex gap-4 text-sm text-muted-foreground">
        <span>{leftLabel}</span>
        <span>→</span>
        <span>{rightLabel}</span>
      </div>
      <pre className="rounded-md border bg-muted/30 p-4 text-xs overflow-x-auto font-mono">
        {diff.map((entry, index) => (
          <div
            key={`${entry.type}-${index}`}
            className={
              entry.type === "removed"
                ? "bg-red-500/10 text-red-700 dark:text-red-300"
                : entry.type === "added"
                  ? "bg-green-500/10 text-green-700 dark:text-green-300"
                  : ""
            }
          >
            {entry.type === "removed"
              ? "- "
              : entry.type === "added"
                ? "+ "
                : "  "}
            {entry.line}
          </div>
        ))}
      </pre>
    </div>
  );
}
