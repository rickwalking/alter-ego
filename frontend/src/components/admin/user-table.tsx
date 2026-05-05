"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { RoleBadge } from "./role-badge";
import { EditUserDialog } from "./edit-user-dialog";
import { DeleteUserDialog } from "./delete-user-dialog";
import { ChangePasswordDialog } from "./change-password-dialog";

interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

interface UserTableProps {
  users: UserItem[];
  onRefresh: () => void;
}

export function UserTable({ users, onRefresh }: UserTableProps) {
  const t = useTranslations("admin");
  const [editUser, setEditUser] = useState<UserItem | null>(null);
  const [deleteUser, setDeleteUser] = useState<UserItem | null>(null);
  const [resetUser, setResetUser] = useState<UserItem | null>(null);

  if (users.length === 0) {
    return (
      <div className="rounded-lg bg-white p-8 text-center shadow">
        <p className="text-gray-500">{t("noUsers")}</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-lg bg-white shadow">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t("nameColumn")}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t("emailColumn")}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t("roleColumn")}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t("statusColumn")}
            </th>
            <th className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-500">
              {t("createdColumn")}
            </th>
            <th className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-500">
              {t("actionsColumn")}
            </th>
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-200 bg-white">
          {users.map((user) => (
            <tr key={user.id}>
              <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900">
                {user.full_name}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {user.email}
              </td>
              <td className="whitespace-nowrap px-6 py-4">
                <RoleBadge role={user.role} />
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {user.is_active ? t("active") : t("inactive")}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-sm text-gray-500">
                {new Date(user.created_at).toLocaleDateString()}
              </td>
              <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium">
                <button
                  onClick={() => setEditUser(user)}
                  className="mr-3 text-primary hover:text-primary-900"
                >
                  {t("edit")}
                </button>
                <button
                  onClick={() => setResetUser(user)}
                  className="mr-3 text-primary hover:text-primary-900"
                >
                  {t("resetPassword")}
                </button>
                <button
                  onClick={() => setDeleteUser(user)}
                  className="text-destructive hover:text-destructive/80"
                >
                  {t("delete")}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {editUser && (
        <EditUserDialog
          user={editUser}
          onClose={() => setEditUser(null)}
          onSuccess={onRefresh}
        />
      )}

      {deleteUser && (
        <DeleteUserDialog
          user={deleteUser}
          onClose={() => setDeleteUser(null)}
          onSuccess={onRefresh}
        />
      )}

      {resetUser && (
        <ChangePasswordDialog
          user={resetUser}
          onClose={() => setResetUser(null)}
          onSuccess={onRefresh}
        />
      )}
    </div>
  );
}
