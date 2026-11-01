import { API_ENDPOINTS, HTTP_METHODS, HTTP_STATUS } from "@/constants/api";
import { ACCOUNT_ERROR_CODES } from "@/constants/auth";
import { USER_PASSWORD_MIN_LENGTH } from "@/constants/admin-users";
import { authenticatedFetch } from "@/lib/authenticated-fetch";
import { errorBodyCode, responseErrorBody } from "@/lib/response-error";
import type { PasswordChangeErrorKey, PasswordChangeValues } from "../types";

/** The message key of a refused change, by stable API error code. */
const ERROR_KEY_BY_CODE: Readonly<Record<string, PasswordChangeErrorKey>> = {
  [ACCOUNT_ERROR_CODES.CURRENT_INCORRECT]: "currentIncorrect",
  [ACCOUNT_ERROR_CODES.UNCHANGED]: "unchanged",
};

/** The message key of a refused change without a known code, by status. */
const ERROR_KEY_BY_STATUS: Readonly<
  Partial<Record<number, PasswordChangeErrorKey>>
> = {
  [HTTP_STATUS.UNPROCESSABLE_ENTITY]: "tooShort",
  [HTTP_STATUS.TOO_MANY_REQUESTS]: "tooMany",
};

/**
 * What is wrong with the form before anything is sent, or null when it can be
 * sent: the API rules (minimum length, a new password that differs from the
 * current one) are checked here too, plus the confirmation.
 */
export function passwordFormError(
  values: PasswordChangeValues,
): PasswordChangeErrorKey | null {
  if (values.next.length < USER_PASSWORD_MIN_LENGTH) {
    return "tooShort";
  }
  if (values.next !== values.confirm) {
    return "mismatch";
  }
  if (values.next === values.current) {
    return "unchanged";
  }
  return null;
}

/** The message key for a failed change-password response. */
export function passwordChangeErrorKey(
  status: number,
  code: string | undefined,
): PasswordChangeErrorKey {
  const byCode = code === undefined ? undefined : ERROR_KEY_BY_CODE[code];
  return byCode ?? ERROR_KEY_BY_STATUS[status] ?? "failed";
}

/**
 * Send the change to the API; null on success, else the message key. A
 * network failure is reported as a failed change, never thrown.
 */
export async function submitPasswordChange(
  values: PasswordChangeValues,
): Promise<PasswordChangeErrorKey | null> {
  try {
    const response = await authenticatedFetch(
      API_ENDPOINTS.AUTH_CHANGE_PASSWORD,
      {
        method: HTTP_METHODS.POST,
        body: JSON.stringify({
          current_password: values.current,
          new_password: values.next,
        }),
      },
    );
    if (response.ok) {
      return null;
    }
    const code = errorBodyCode(await responseErrorBody(response));
    return passwordChangeErrorKey(response.status, code);
  } catch {
    return "failed";
  }
}
