"use client";

import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { mapPersonaProfileToCardProps } from "@/modules/editorial-operations";
import { NeonPersonaCard, type PersonaProfile } from "@/modules/persona";

interface PersonaTileProps {
  persona: PersonaProfile;
  onEdit: () => void;
  onDelete: () => void;
}

/** A persona card with its Edit and Delete actions. */
export function PersonaTile({
  persona,
  onEdit,
  onDelete,
}: Readonly<PersonaTileProps>): React.ReactElement {
  const t = useTranslations("personas.card");
  return (
    <div className="flex flex-col gap-2">
      <NeonPersonaCard {...mapPersonaProfileToCardProps(persona)} />
      <div className="flex justify-end gap-1">
        <NeonButton
          variant="ghost"
          size="sm"
          aria-label={t("editLabel", { name: persona.name })}
          onClick={onEdit}
        >
          {t("edit")}
        </NeonButton>
        <NeonButton
          variant="ghost"
          size="sm"
          aria-label={t("deleteLabel", { name: persona.name })}
          onClick={onDelete}
        >
          {t("delete")}
        </NeonButton>
      </div>
    </div>
  );
}
