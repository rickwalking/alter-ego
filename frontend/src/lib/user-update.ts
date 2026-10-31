import { USER_FULL_NAME_MAX_LENGTH } from "@/constants/admin-users";

/** The edit-dialog values an admin can change (the email is fixed). */
export interface UserUpdateDraft {
  role: string;
  isActive: boolean;
  fullName: string;
}

interface UserUpdatePayload {
  role: string;
  is_active: boolean;
  full_name?: string;
}

/** True when the trimmed name has 1 to 255 characters, as the API requires. */
export function isValidFullName(name: string): boolean {
  const trimmed = name.trim();
  return trimmed.length > 0 && trimmed.length <= USER_FULL_NAME_MAX_LENGTH;
}

/**
 * The `PATCH /api/admin/users/{id}` body for a draft.
 *
 * `full_name` is trimmed and sent only when it differs from the current name,
 * so a role- or status-only save keeps the request shape it always had.
 */
export function buildUserUpdatePayload(
  currentName: string,
  draft: UserUpdateDraft,
): UserUpdatePayload {
  const payload: UserUpdatePayload = {
    role: draft.role,
    is_active: draft.isActive,
  };
  const fullName = draft.fullName.trim();
  if (fullName !== currentName) {
    payload.full_name = fullName;
  }
  return payload;
}
