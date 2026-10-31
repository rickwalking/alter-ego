import {
  USER_FULL_NAME_FIELD,
  USER_FULL_NAME_MAX_LENGTH,
} from "@/constants/admin-users";

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

/**
 * True when the trimmed name has 1 to 255 characters, as the API requires.
 *
 * Counts code points (like Python's `len`), not UTF-16 units, so an emoji
 * counts as one character on both sides.
 */
export function isValidFullName(name: string): boolean {
  const length = Array.from(name.trim()).length;
  return length > 0 && length <= USER_FULL_NAME_MAX_LENGTH;
}

function hasFullNameLoc(item: unknown): boolean {
  if (item === null || typeof item !== "object" || !("loc" in item)) {
    return false;
  }
  return Array.isArray(item.loc) && item.loc.includes(USER_FULL_NAME_FIELD);
}

/**
 * True when a FastAPI 422 body is a validation list with an error on the name
 * (its `loc` includes `full_name`); any other body is not a name error.
 */
export function isFullNameValidationError(body: unknown): boolean {
  if (body === null || typeof body !== "object" || !("detail" in body)) {
    return false;
  }
  return Array.isArray(body.detail) && body.detail.some(hasFullNameLoc);
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
