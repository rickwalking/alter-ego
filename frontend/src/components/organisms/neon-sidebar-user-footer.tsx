"use client";

import Image from "next/image";
import Link from "next/link";
import { useTranslations } from "next-intl";
import { NeonIcon } from "@/components/atoms/neon-icon";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import {
  TEXT,
  NEON_BORDER_LIGHT,
  NEON_BORDER_STRONG,
  NEON_BORDER_SUBTLE,
  TEXT_DIM,
  TEXT_MUTED,
} from "@/constants/neon";
import type { useAuth } from "@/modules/identity";
import { SIDEBAR_AVATAR_SIZE } from "@/components/organisms/constants";

type AuthUser = NonNullable<ReturnType<typeof useAuth>["user"]>;

const FOOTER_BUTTON_CLASS =
  "flex shrink-0 items-center justify-center rounded-md h-7 w-7 [@media(pointer:coarse)]:h-11 [@media(pointer:coarse)]:w-11";
const KEY_ICON_PATH =
  "M15 7a4 4 0 1 1-3.9 4.9L3 20v-3h3v-3h3l2.1-2.1A4 4 0 0 1 15 7zM16 9h.01";

/** The footer link to the change-password page. */
function ChangePasswordLink(): React.ReactElement {
  const t = useTranslations("account.password");
  return (
    <Link
      href={DASHBOARD_ROUTES.ACCOUNT_PASSWORD}
      aria-label={t("sidebarLink")}
      title={t("sidebarLink")}
      className={FOOTER_BUTTON_CLASS}
      style={{
        border: `1px solid ${NEON_BORDER_LIGHT}`,
        color: TEXT_MUTED,
      }}
    >
      <NeonIcon path={KEY_ICON_PATH} size={14} />
    </Link>
  );
}

/**
 * The signed-in user's avatar, name, email, change-password link and logout.
 *
 * The link and the logout button are 44px+ tap targets on touch devices and
 * compact for a mouse.
 */
export function SidebarUserFooter({
  user,
  onLogout,
}: Readonly<{
  user: AuthUser;
  onLogout: () => void;
}>): React.ReactElement {
  return (
    <div
      style={{
        padding: "12px",
        borderTop: `1px solid ${NEON_BORDER_SUBTLE}`,
        display: "flex",
        alignItems: "center",
        gap: "10px",
      }}
    >
      <Image
        src="/about-pedro.jpg"
        alt="Pedro"
        width={SIDEBAR_AVATAR_SIZE}
        height={SIDEBAR_AVATAR_SIZE}
        style={{
          borderRadius: "50%",
          border: `1px solid ${NEON_BORDER_STRONG}`,
          objectFit: "cover",
        }}
      />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div
          style={{
            fontSize: "12px",
            fontWeight: 600,
            color: TEXT,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {user.full_name}
        </div>
        <div
          style={{
            fontFamily: "'JetBrains Mono', ui-monospace, monospace",
            fontSize: "9px",
            color: TEXT_DIM,
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {user.email}
        </div>
      </div>
      <ChangePasswordLink />
      <button
        type="button"
        onClick={onLogout}
        aria-label="Logout"
        title="Logout"
        className={FOOTER_BUTTON_CLASS}
        style={{
          border: `1px solid ${NEON_BORDER_LIGHT}`,
          background: "transparent",
          color: TEXT_MUTED,
          cursor: "pointer",
        }}
      >
        <NeonIcon
          path="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4M16 17l5-5M21 12H9"
          size={14}
        />
      </button>
    </div>
  );
}
