import {
  ADMIN_USER_ERROR_CODES,
  USER_EMAIL_FIELD,
  USER_FULL_NAME_FIELD,
  USER_PASSWORD_FIELD,
  USER_PASSWORD_MIN_LENGTH,
} from "@/constants/admin-users";
import { HTTP_STATUS } from "@/constants/api";
import { errorBodyCode, validationErrorFields } from "@/lib/response-error";

/** `admin` message key for each stable API error code. */
const CODE_MESSAGE_KEYS: Readonly<Record<string, string>> = {
  [ADMIN_USER_ERROR_CODES.EMAIL_EXISTS]: "emailTaken",
  [ADMIN_USER_ERROR_CODES.LAST_ADMIN]: "lastAdminError",
  [ADMIN_USER_ERROR_CODES.SELF_DELETE]: "selfDeleteError",
};

const USER_NOT_FOUND_KEY = "userNotFound";
const MIN_LENGTH_MESSAGE_KEY = "minLengthNotMet";

/** The create-user fields a validation error can point at. */
export type CreateUserField =
  | typeof USER_EMAIL_FIELD
  | typeof USER_FULL_NAME_FIELD
  | typeof USER_PASSWORD_FIELD;

/** `admin` message key shown under each create-user field when it is invalid. */
export const CREATE_FIELD_MESSAGE_KEYS: Readonly<
  Record<CreateUserField, string>
> = {
  [USER_EMAIL_FIELD]: "emailInvalid",
  [USER_FULL_NAME_FIELD]: "createNameInvalid",
  [USER_PASSWORD_FIELD]: MIN_LENGTH_MESSAGE_KEY,
};

/** Field -> `admin` message key, for the fields that are invalid. */
export type CreateFieldErrors = Partial<Record<CreateUserField, string>>;

/**
 * The `admin` message key for a failed admin user request, from its stable
 * `code` first and its status second (404: the user is gone); undefined when
 * neither is known, so the caller shows its own translated fallback. The
 * English `detail` is never shown.
 */
export function adminErrorKey(
  status: number,
  body: unknown,
): string | undefined {
  const code = errorBodyCode(body);
  if (code !== undefined && Object.hasOwn(CODE_MESSAGE_KEYS, code)) {
    return CODE_MESSAGE_KEYS[code];
  }
  return status === HTTP_STATUS.NOT_FOUND ? USER_NOT_FOUND_KEY : undefined;
}

function isCreateUserField(field: string): field is CreateUserField {
  return Object.hasOwn(CREATE_FIELD_MESSAGE_KEYS, field);
}

/** The invalid create-user fields of a 422 body (no entry for other fields). */
export function createFieldErrors(
  status: number,
  body: unknown,
): CreateFieldErrors {
  if (status !== HTTP_STATUS.UNPROCESSABLE_ENTITY) {
    return {};
  }
  const errors: CreateFieldErrors = {};
  for (const field of validationErrorFields(body).filter(isCreateUserField)) {
    errors[field] = CREATE_FIELD_MESSAGE_KEYS[field];
  }
  return errors;
}

/**
 * True when a typed password is too short for the API. A blank password is
 * fine: the API then generates a temporary one. Counts code points, like the
 * API's `len`.
 */
export function isPasswordTooShort(password: string): boolean {
  const length = Array.from(password).length;
  return length > 0 && length < USER_PASSWORD_MIN_LENGTH;
}
