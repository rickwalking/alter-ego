"use client";

import { useTranslations } from "next-intl";
import {
  USER_FILTER_ROLE_ADMIN,
  USER_FILTER_ROLE_ALL,
  USER_FILTER_ROLE_EDITOR,
  USER_FILTER_STATUS_ACTIVE,
  USER_FILTER_STATUS_ALL,
  USER_FILTER_STATUS_INACTIVE,
} from "@/constants/admin-users";

interface UserFilterToolbarProps {
  query: string;
  role: string;
  status: string;
  onQueryChange: (value: string) => void;
  onRoleChange: (value: string) => void;
  onStatusChange: (value: string) => void;
}

const SEARCH_INPUT_ID = "user-search";
const ROLE_SELECT_ID = "user-role-filter";
const STATUS_SELECT_ID = "user-status-filter";
const FIELD_CLASS =
  "w-full rounded-md border border-gray-300 px-3 py-2 text-sm text-gray-900 focus:outline-none focus:ring-2 focus:ring-primary-500";
const LABEL_CLASS = "mb-1 block text-sm font-medium text-gray-700";

export function UserFilterToolbar({
  query,
  role,
  status,
  onQueryChange,
  onRoleChange,
  onStatusChange,
}: Readonly<UserFilterToolbarProps>) {
  const t = useTranslations("admin");

  return (
    <div className="mb-4 flex flex-wrap items-end gap-3 rounded-lg bg-white p-4 shadow">
      <div className="min-w-56 flex-1">
        <label htmlFor={SEARCH_INPUT_ID} className={LABEL_CLASS}>
          {t("searchLabel")}
        </label>
        <input
          id={SEARCH_INPUT_ID}
          type="search"
          value={query}
          onChange={(event) => onQueryChange(event.target.value)}
          placeholder={t("searchPlaceholder")}
          className={FIELD_CLASS}
        />
      </div>
      <div className="w-40">
        <label htmlFor={ROLE_SELECT_ID} className={LABEL_CLASS}>
          {t("roleLabel")}
        </label>
        <select
          id={ROLE_SELECT_ID}
          value={role}
          onChange={(event) => onRoleChange(event.target.value)}
          className={FIELD_CLASS}
        >
          <option value={USER_FILTER_ROLE_ALL}>{t("roleFilterAll")}</option>
          <option value={USER_FILTER_ROLE_ADMIN}>{t("adminRole")}</option>
          <option value={USER_FILTER_ROLE_EDITOR}>{t("editorRole")}</option>
        </select>
      </div>
      <div className="w-40">
        <label htmlFor={STATUS_SELECT_ID} className={LABEL_CLASS}>
          {t("statusColumn")}
        </label>
        <select
          id={STATUS_SELECT_ID}
          value={status}
          onChange={(event) => onStatusChange(event.target.value)}
          className={FIELD_CLASS}
        >
          <option value={USER_FILTER_STATUS_ALL}>{t("statusFilterAll")}</option>
          <option value={USER_FILTER_STATUS_ACTIVE}>{t("active")}</option>
          <option value={USER_FILTER_STATUS_INACTIVE}>{t("inactive")}</option>
        </select>
      </div>
    </div>
  );
}
