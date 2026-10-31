"use client";

import { useLocale, useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { TOUCH_TARGET_CLASS } from "@/constants/admin-users";
import { formatLocaleDate } from "@/lib/locale-format";
import { cn } from "@/lib/utils";
import { RoleBadge } from "./role-badge";
import type { UserItem } from "./user-dialog-parts";

/** The three row actions, each opening its dialog for the user. */
export interface UserRowHandlers {
  onEdit: (user: UserItem) => void;
  onReset: (user: UserItem) => void;
  onDelete: (user: UserItem) => void;
}

interface UserRowsProps {
  users: UserItem[];
  handlers: UserRowHandlers;
}

const HEADER_CELL_CLASS =
  "px-4 py-3 text-left text-xs font-medium uppercase tracking-wider text-text-muted";
const CELL_CLASS = "px-4 py-3 text-sm text-text-muted";
const ACTION_BUTTON_CLASS = cn(TOUCH_TARGET_CLASS, "px-3");

interface UserActionsProps {
  user: UserItem;
  handlers: UserRowHandlers;
  className?: string;
}

/** Edit, reset password and delete: buttons at least 44 px tall to tap. */
function UserActions({
  user,
  handlers,
  className,
}: Readonly<UserActionsProps>) {
  const t = useTranslations("admin");
  return (
    <div className={cn("flex flex-wrap gap-1", className)}>
      <NeonButton
        variant="ghost"
        size="sm"
        onClick={() => handlers.onEdit(user)}
        className={cn(ACTION_BUTTON_CLASS, "text-neon-cyan")}
      >
        {t("edit")}
      </NeonButton>
      <NeonButton
        variant="ghost"
        size="sm"
        onClick={() => handlers.onReset(user)}
        className={cn(ACTION_BUTTON_CLASS, "text-neon-cyan")}
      >
        {t("resetPassword")}
      </NeonButton>
      <NeonButton
        variant="ghost"
        size="sm"
        onClick={() => handlers.onDelete(user)}
        className={cn(ACTION_BUTTON_CLASS, "text-neon-red")}
      >
        {t("delete")}
      </NeonButton>
    </div>
  );
}

function useStatusLabel(): (user: UserItem) => string {
  const t = useTranslations("admin");
  return (user) => (user.is_active ? t("active") : t("inactive"));
}

/**
 * The user list as a table (tablet and desktop). The table scrolls inside
 * its own box, so a narrow window never scrolls the whole page sideways.
 */
export function UserTableView({ users, handlers }: Readonly<UserRowsProps>) {
  const t = useTranslations("admin");
  const locale = useLocale();
  const statusLabel = useStatusLabel();
  return (
    <div className="overflow-x-auto rounded-lg border border-[var(--color-neon-card-border)] bg-bg-card">
      <table className="min-w-full divide-y divide-[var(--color-neon-card-border)]">
        <thead>
          <tr>
            <th className={HEADER_CELL_CLASS}>{t("nameColumn")}</th>
            <th className={HEADER_CELL_CLASS}>{t("emailColumn")}</th>
            <th className={HEADER_CELL_CLASS}>{t("roleColumn")}</th>
            <th className={HEADER_CELL_CLASS}>{t("statusColumn")}</th>
            <th className={HEADER_CELL_CLASS}>{t("createdColumn")}</th>
            <th className={cn(HEADER_CELL_CLASS, "text-right")}>
              {t("actionsColumn")}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-[var(--color-neon-card-border)]">
          {users.map((user) => (
            <tr key={user.id}>
              <td className={cn(CELL_CLASS, "font-medium text-text-primary")}>
                {user.full_name}
              </td>
              <td className={cn(CELL_CLASS, "break-all")}>{user.email}</td>
              <td className={CELL_CLASS}>
                <RoleBadge role={user.role} />
              </td>
              <td className={CELL_CLASS}>{statusLabel(user)}</td>
              <td className={cn(CELL_CLASS, "whitespace-nowrap")}>
                {formatLocaleDate(user.created_at, locale)}
              </td>
              <td className={CELL_CLASS}>
                <UserActions
                  user={user}
                  handlers={handlers}
                  className="justify-end"
                />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

/** The user list as stacked cards (phones): nothing clipped, no side scroll. */
export function UserCardList({ users, handlers }: Readonly<UserRowsProps>) {
  const t = useTranslations("admin");
  const locale = useLocale();
  const statusLabel = useStatusLabel();
  return (
    <ul className="space-y-3">
      {users.map((user) => (
        <li
          key={user.id}
          className="rounded-lg border border-[var(--color-neon-card-border)] bg-bg-card p-4"
        >
          <p className="font-medium text-text-primary">{user.full_name}</p>
          <p className="mt-1 break-all text-sm text-text-muted">{user.email}</p>
          <div className="mt-3 flex flex-wrap items-center gap-2 text-sm text-text-muted">
            <RoleBadge role={user.role} />
            <span>{statusLabel(user)}</span>
            <span aria-hidden="true">·</span>
            <span>
              {t("createdColumn")}: {formatLocaleDate(user.created_at, locale)}
            </span>
          </div>
          <UserActions user={user} handlers={handlers} className="mt-3" />
        </li>
      ))}
    </ul>
  );
}
