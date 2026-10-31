"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { USER_FILTER_ROLE_ADMIN } from "@/constants/admin-users";
import type { NeonBadgeVariant } from "@/schemas/neon-badge";

/**
 * Amber for admins, cyan for editors: both keep their text above 4.5:1 on the
 * card (the dashboard's magenta and the old light-blue badge do not).
 */
export const ADMIN_ROLE_BADGE_VARIANT: NeonBadgeVariant = "amber";
export const EDITOR_ROLE_BADGE_VARIANT: NeonBadgeVariant = "cyan";

interface RoleBadgeProps {
  role: string;
}

/** The user's role as a translated neon badge. */
export function RoleBadge({ role }: Readonly<RoleBadgeProps>) {
  const t = useTranslations("admin");
  const isAdmin = role === USER_FILTER_ROLE_ADMIN;
  return (
    <NeonBadge
      variant={isAdmin ? ADMIN_ROLE_BADGE_VARIANT : EDITOR_ROLE_BADGE_VARIANT}
    >
      {isAdmin ? t("adminRole") : t("editorRole")}
    </NeonBadge>
  );
}
