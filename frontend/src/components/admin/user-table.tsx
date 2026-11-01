"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { USER_ACTIONS, USER_CARDS_MEDIA_QUERY } from "@/constants/admin-users";
import { refocusUserAction } from "@/lib/refocus-user-action";
import { useMediaQuery } from "@/lib/use-media-query";
import { EditUserDialog } from "./edit-user-dialog";
import { DeleteUserDialog } from "./delete-user-dialog";
import { ChangePasswordDialog } from "./change-password-dialog";
import type { UserItem } from "./user-dialog-parts";
import { UserCardList, type UserRowHandlers, UserTableView } from "./user-rows";

interface UserTableProps {
  users: UserItem[];
  onRefresh: () => void;
  /**
   * Id of the only active admin of the FULL list (not just the filtered
   * rows), whose role and active status the edit dialog locks.
   */
  lastActiveAdminId?: string;
}

/**
 * The admin user list: a table from tablet width up, stacked cards on a
 * phone. Each row action opens its modal dialog; closing it brings focus back
 * to that action even if the layout swapped meanwhile.
 */
export function UserTable({
  users,
  onRefresh,
  lastActiveAdminId,
}: Readonly<UserTableProps>) {
  const t = useTranslations("admin");
  const isPhone = useMediaQuery(USER_CARDS_MEDIA_QUERY);
  const [editUser, setEditUser] = useState<UserItem | null>(null);
  const [deleteUser, setDeleteUser] = useState<UserItem | null>(null);
  const [resetUser, setResetUser] = useState<UserItem | null>(null);
  const handlers: UserRowHandlers = {
    onEdit: setEditUser,
    onReset: setResetUser,
    onDelete: setDeleteUser,
  };

  if (users.length === 0) {
    return (
      <div className="rounded-lg border border-[var(--color-neon-card-border)] bg-bg-card p-8 text-center">
        <p className="text-text-muted">{t("noUsers")}</p>
      </div>
    );
  }

  const List = isPhone ? UserCardList : UserTableView;
  return (
    <>
      <List users={users} handlers={handlers} />

      {editUser && (
        <EditUserDialog
          user={editUser}
          isLastActiveAdmin={editUser.id === lastActiveAdminId}
          onClose={() => {
            setEditUser(null);
            refocusUserAction(USER_ACTIONS.EDIT, editUser.id);
          }}
          onSuccess={onRefresh}
        />
      )}

      {deleteUser && (
        <DeleteUserDialog
          user={deleteUser}
          onClose={() => {
            setDeleteUser(null);
            refocusUserAction(USER_ACTIONS.DELETE, deleteUser.id);
          }}
          onSuccess={onRefresh}
        />
      )}

      {resetUser && (
        <ChangePasswordDialog
          user={resetUser}
          onClose={() => {
            setResetUser(null);
            refocusUserAction(USER_ACTIONS.RESET, resetUser.id);
          }}
          onSuccess={onRefresh}
        />
      )}
    </>
  );
}
