"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { CreateUserDialog } from "@/components/admin/create-user-dialog";
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
  const [error, setError] = useState("");
  const [isCreateOpen, setIsCreateOpen] = useState(false);

  const fetchUsers = async () => {
    setIsLoading(true);
    setError("");
    try {
      const response = await fetch("/api/admin/users", {
        credentials: "include",
      });
      if (!response.ok) {
        throw new Error("Failed to fetch users");
      }
      const data = (await response.json()) as {
        items: UserItem[];
        total: number;
      };
      setUsers(data.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUsers();
  }, []);

  const handleUserCreated = () => {
    setIsCreateOpen(false);
    fetchUsers();
  };

  return (
    <div>
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">
            {t("usersTitle")}
          </h1>
          <p className="mt-1 text-sm text-gray-500">
            {t("usersSubtitle", { count: users.length })}
          </p>
        </div>
        <button
          onClick={() => setIsCreateOpen(true)}
          className="rounded-md bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary-600"
        >
          {t("createUser")}
        </button>
      </div>

      {error && (
        <div className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {isLoading ? (
        <div className="py-8 text-center text-gray-500">{t("loading")}</div>
      ) : (
        <UserTable users={users} onRefresh={fetchUsers} />
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
