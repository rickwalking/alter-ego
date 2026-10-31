"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { mapPersonaProfileToCardProps } from "@/modules/editorial-operations";
import { NeonPersonaCard, type PersonaProfile } from "@/modules/persona";

/** Keeps the card actions at the 44 px minimum touch target. */
const TOUCH_TARGET_CLASS = "min-h-11 min-w-11";

interface PersonaTileProps {
  persona: PersonaProfile;
  onEdit: () => void;
  onDelete: () => void;
}

/** A persona card with its Edit and Delete actions in the card footer. */
export function PersonaTile({
  persona,
  onEdit,
  onDelete,
}: Readonly<PersonaTileProps>): React.ReactElement {
  const t = useTranslations("personas.card");
  const card = mapPersonaProfileToCardProps(persona, {
    description: t("noDescription"),
    role: t("defaultRole"),
  });
  return (
    <NeonPersonaCard
      {...card}
      footer={
        <>
          <NeonButton
            variant="ghost"
            size="sm"
            className={TOUCH_TARGET_CLASS}
            aria-label={t("editLabel", { name: persona.name })}
            onClick={onEdit}
          >
            {t("edit")}
          </NeonButton>
          <NeonButton
            variant="ghost"
            size="sm"
            className={TOUCH_TARGET_CLASS}
            aria-label={t("deleteLabel", { name: persona.name })}
            onClick={onDelete}
          >
            {t("delete")}
          </NeonButton>
        </>
      }
    />
  );
}
