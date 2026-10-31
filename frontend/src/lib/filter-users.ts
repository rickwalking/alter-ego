import {
  USER_FILTER_ROLE_ALL,
  USER_FILTER_STATUS_ACTIVE,
  USER_FILTER_STATUS_INACTIVE,
} from "@/constants/admin-users";

export interface UserFilterTarget {
  full_name: string;
  email: string;
  role: string;
  is_active: boolean;
}

export interface UserFilter {
  query: string;
  role: string;
  status: string;
}

export function normalizeSearchText(text: string): string {
  return text
    .normalize("NFD")
    .replace(/\p{Diacritic}/gu, "")
    .toLowerCase();
}

function matchesRole(user: UserFilterTarget, role: string): boolean {
  return role === USER_FILTER_ROLE_ALL || user.role === role;
}

function matchesStatus(user: UserFilterTarget, status: string): boolean {
  if (status === USER_FILTER_STATUS_ACTIVE) return user.is_active;
  if (status === USER_FILTER_STATUS_INACTIVE) return !user.is_active;
  return true;
}

function matchesQuery(user: UserFilterTarget, needle: string): boolean {
  if (needle === "") return true;
  return (
    normalizeSearchText(user.full_name).includes(needle) ||
    normalizeSearchText(user.email).includes(needle)
  );
}

export function filterUsers<T extends UserFilterTarget>(
  users: readonly T[],
  filter: UserFilter,
): T[] {
  const needle = normalizeSearchText(filter.query.trim());
  return users.filter(
    (user) =>
      matchesRole(user, filter.role) &&
      matchesStatus(user, filter.status) &&
      matchesQuery(user, needle),
  );
}
