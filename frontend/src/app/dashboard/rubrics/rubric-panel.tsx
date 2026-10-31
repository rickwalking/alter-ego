import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { BG_CARD, NEON_CARD_BORDER } from "@/constants/neon";
import {
  RUBRIC_HEADER_BORDER,
  type RubricData,
} from "@/modules/editorial-operations";
import { RubricBadge } from "@/app/dashboard/rubrics/rubric-badge";
import { RubricCriteriaTable } from "@/app/dashboard/rubrics/rubric-criteria-table";
import { RubricDefaultBadge } from "@/app/dashboard/rubrics/rubric-default-badge";
import { useContentTypeLabel } from "@/app/dashboard/rubrics/use-rubric-labels";

/** WCAG 2.5.5: the card's actions are at least 44 × 44 px to tap. */
const TOUCH_TARGET = "min-h-11 min-w-11";

interface RubricPanelProps {
  rubric: RubricData;
  onEdit: () => void;
  /** Omitted for the default rubric, which the API refuses to delete. */
  onDelete?: () => void;
}

function RubricTags({
  rubric,
}: Readonly<Pick<RubricPanelProps, "rubric">>): React.ReactElement | null {
  const label = useContentTypeLabel();
  if (rubric.contentTypes.length === 0 && !rubric.isDefault) {
    return null;
  }
  return (
    <div className="flex flex-wrap items-center gap-2">
      {rubric.contentTypes.map((tag) => (
        <RubricBadge key={tag.type} label={label(tag.type)} color={tag.color} />
      ))}
      {rubric.isDefault && <RubricDefaultBadge />}
    </div>
  );
}

function RubricActions({
  rubric,
  onEdit,
  onDelete,
}: Readonly<RubricPanelProps>): React.ReactElement {
  const t = useTranslations("rubrics.panel");
  return (
    <div className="flex flex-wrap items-center gap-2">
      <NeonButton
        variant="ghost"
        size="sm"
        className={TOUCH_TARGET}
        aria-label={t("editLabel", { name: rubric.title })}
        onClick={onEdit}
      >
        {t("edit")}
      </NeonButton>
      {onDelete && (
        <NeonButton
          variant="ghost"
          size="sm"
          className={TOUCH_TARGET}
          aria-label={t("deleteLabel", { name: rubric.title })}
          onClick={onDelete}
        >
          {t("delete")}
        </NeonButton>
      )}
    </div>
  );
}

/**
 * One rubric card: title, content types, default mark and actions in a header
 * that wraps on a narrow screen, then its criteria.
 */
export function RubricPanel(
  props: Readonly<RubricPanelProps>,
): React.ReactElement {
  const { rubric } = props;
  return (
    <div
      style={{
        background: BG_CARD,
        border: `1px solid ${NEON_CARD_BORDER}`,
        borderRadius: 8,
        overflow: "hidden",
        marginBottom: 16,
      }}
    >
      <div
        className="rubric-panel-header flex flex-wrap items-center justify-between gap-x-4 gap-y-2"
        style={{
          padding: "16px 20px",
          borderBottom: `1px solid ${RUBRIC_HEADER_BORDER}`,
        }}
      >
        <div className="flex min-w-0 flex-col gap-2">
          <h3
            className="m-0 min-w-0 break-words"
            style={{
              fontSize: 15,
              fontWeight: 700,
              color: "var(--color-foreground, #ededed)",
            }}
          >
            {rubric.title}
          </h3>
          <RubricTags rubric={rubric} />
        </div>
        <RubricActions {...props} />
      </div>
      <RubricCriteriaTable criteria={rubric.criteria} />
    </div>
  );
}
