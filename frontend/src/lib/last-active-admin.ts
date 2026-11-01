import { USER_ROLE_ADMIN } from "@/constants/admin-users";

/** The fields the last-active-admin rule reads from a listed user. */
interface AdminCandidate {
  id: string;
  role: string;
  is_active: boolean;
}

function isActiveAdmin(user: AdminCandidate): boolean {
  return user.role === USER_ROLE_ADMIN && user.is_active;
}

/**
 * The id of the only active admin of the full user list, else undefined
 * (no active admin, or more than one). The API refuses to demote or
 * deactivate that user, so the dialog locks those controls. Inactive admins
 * do not count: they cannot sign in.
 */
export function lastActiveAdminId(
  users: readonly AdminCandidate[],
): string | undefined {
  const activeAdmins = users.filter(isActiveAdmin);
  return activeAdmins.length === 1 ? activeAdmins[0]?.id : undefined;
}
