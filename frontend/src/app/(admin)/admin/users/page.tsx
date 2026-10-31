"use client";

import { useEffect, useMemo, useState } from "react";
import { useTranslations } from "next-intl";
import {
  TOUCH_TARGET_CLASS,
  USER_FILTER_ROLE_ALL,
  USER_FILTER_STATUS_ALL,
} from "@/constants/admin-users";
import { filterUsers } from "@/lib/filter-users";
import { NeonButton } from "@/components/atoms/neon-button";
import { CreateUserDialog } from "@/components/admin/create-user-dialog";
import { UserFilterToolbar } from "@/components/admin/user-filter-toolbar";
import { UserTable } from "@/components/admin/user-table";

interface UserItem {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function UsersPage() {
  const t = useTranslations("admin");
  const [users, setUsers] = useState<UserItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [loadFailed, setLoadFailed] = useState(false);
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [roleFilter, setRoleFilter] = useState(USER_FILTER_ROLE_ALL);
  const [statusFilter, setStatusFilter] = useState(USER_FILTER_STATUS_ALL);

  const fetchUsers = async () => {
    setIsLoading(true);
    setLoadFailed(false);
    try {
      const response = await fetch("/api/admin/users", {
        credentials: "include",
      });
      if (!response.ok) {
        setLoadFailed(true);
        return;
      }
      const data = (await response.json()) as {
        items: UserItem[];
        total: number;
      };
      setUsers(data.items);
    } catch {
      setLoadFailed(true);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    void fetchUsers();
  }, []);

  const handleUserCreated = () => {
    setIsCreateOpen(false);
    void fetchUsers();
  };

  const filteredUsers = useMemo(
    () =>
      filterUsers(users, {
        query: searchQuery,
        role: roleFilter,
        status: statusFilter,
      }),
    [users, searchQuery, roleFilter, statusFilter],
  );

  const hasActiveFilters =
    searchQuery.trim() !== "" ||
    roleFilter !== USER_FILTER_ROLE_ALL ||
    statusFilter !== USER_FILTER_STATUS_ALL;

  return (
    <div>
      <div className="mb-6 flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-text-primary">
            {t("usersTitle")}
          </h1>
          <p className="mt-1 text-sm text-text-muted">
            {t("usersSubtitle", { count: users.length })}
          </p>
        </div>
        <NeonButton
          onClick={() => setIsCreateOpen(true)}
          className={TOUCH_TARGET_CLASS}
        >
          {t("createUser")}
        </NeonButton>
      </div>

      {loadFailed && (
        <div
          role="alert"
          className="mb-4 rounded-md border border-neon-red/30 bg-neon-red/10 p-3 text-sm text-text-primary"
        >
          {t("loadError")}
        </div>
      )}

      {isLoading ? (
        <div className="py-8 text-center text-text-muted">{t("loading")}</div>
      ) : (
        <>
          <UserFilterToolbar
            query={searchQuery}
            role={roleFilter}
            status={statusFilter}
            onQueryChange={setSearchQuery}
            onRoleChange={setRoleFilter}
            onStatusChange={setStatusFilter}
          />
          {filteredUsers.length === 0 && hasActiveFilters && !loadFailed ? (
            <div className="rounded-lg border border-[var(--color-neon-card-border)] bg-bg-card p-8 text-center">
              <p className="text-text-muted">{t("noUsersMatch")}</p>
            </div>
          ) : (
            <UserTable
              users={filteredUsers}
              onRefresh={() => {
                void fetchUsers();
              }}
            />
          )}
        </>
      )}

      {isCreateOpen && (
        <CreateUserDialog
          onClose={() => setIsCreateOpen(false)}
          onSuccess={handleUserCreated}
        />
      )}
    </div>
  );
}
