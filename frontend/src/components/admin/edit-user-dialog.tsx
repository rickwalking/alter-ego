"use client";

import { useId, useState } from "react";
import { useTranslations } from "next-intl";
import { HTTP_STATUS } from "@/constants/api";
import { USER_FULL_NAME_MAX_LENGTH } from "@/constants/admin-users";
import { adminErrorKey } from "@/lib/admin-user-errors";
import { responseErrorBody } from "@/lib/response-error";
import {
  buildUserUpdatePayload,
  isFullNameValidationError,
  isValidFullName,
  type UserUpdateDraft,
} from "@/lib/user-update";
import { cn } from "@/lib/utils";
import {
  DIALOG_MUTED_TEXT_CLASS,
  FIELD_INPUT_CLASS,
  FIELD_LABEL_CLASS,
  UserDialogActions,
  UserDialogShell,
  useDialogStatus,
  UserRoleSelect,
  type UserDialogProps,
  type UserItem,
} from "./user-dialog-parts";
import { UserActiveField } from "./user-active-field";

const NAME_INVALID_KEY = "nameInvalid";
const LAST_ACTIVE_ADMIN_LOCKED_KEY = "lastActiveAdminLocked";
const UPDATE_ERROR_KEY = "updateError";

/**
 * The `admin` message key for a failed update: the stable API code first
 * (last admin, user gone), the name message for a 422 whose errors point at
 * `full_name`, else the generic one (any other 422 included). The English
 * `detail` is never shown.
 */
async function updateFailureKey(response: Response): Promise<string> {
  const body = await responseErrorBody(response);
  const known = adminErrorKey(response.status, body);
  if (known !== undefined) {
    return known;
  }
  const isNameError =
    response.status === HTTP_STATUS.UNPROCESSABLE_ENTITY &&
    isFullNameValidationError(body);
  return isNameError ? NAME_INVALID_KEY : UPDATE_ERROR_KEY;
}

/** PATCH the draft for `user`; the message key of a failure, else undefined. */
async function sendUserUpdate(
  user: UserItem,
  draft: UserUpdateDraft,
): Promise<string | undefined> {
  const response = await fetch(`/api/admin/users/${user.id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify(buildUserUpdatePayload(user.full_name, draft)),
  });
  return response.ok ? undefined : updateFailureKey(response);
}

interface FullNameFieldProps {
  value: string;
  onChange: (value: string) => void;
  /** Id of the error banner when the name is invalid, else undefined. */
  errorId?: string;
}

/**
 * The labelled, editable full-name input of the edit dialog; when `errorId`
 * is set it is marked invalid and described by that error banner.
 */
function FullNameField({
  value,
  onChange,
  errorId,
}: Readonly<FullNameFieldProps>) {
  const t = useTranslations("admin");
  const inputId = useId();
  return (
    <div>
      <label htmlFor={inputId} className={FIELD_LABEL_CLASS}>
        {t("fullNameLabel")}
      </label>
      <input
        id={inputId}
        type="text"
        autoComplete="name"
        maxLength={USER_FULL_NAME_MAX_LENGTH}
        aria-invalid={errorId !== undefined}
        aria-describedby={errorId}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className={cn(FIELD_INPUT_CLASS, "focus-visible:ring-2")}
      />
    </div>
  );
}

interface EditUserDialogProps extends UserDialogProps {
  /**
   * True when `user` is the only active admin: the API refuses to demote or
   * deactivate them, so the role select and the active checkbox are locked
   * and explained.
   */
  isLastActiveAdmin?: boolean;
}

export function EditUserDialog({
  user,
  onClose,
  onSuccess,
  isLastActiveAdmin = false,
}: Readonly<EditUserDialogProps>) {
  const t = useTranslations("admin");
  const lockHintId = useId();
  const lockedBy = isLastActiveAdmin ? lockHintId : undefined;
  const [role, setRole] = useState(user.role);
  const [isActive, setIsActive] = useState(user.is_active);
  const [fullName, setFullName] = useState(user.full_name);
  const status = useDialogStatus();
  const errorId = useId();
  const nameErrorId =
    status.error === t(NAME_INVALID_KEY) ? errorId : undefined;

  const handleSubmit = async (e: React.SubmitEvent) => {
    e.preventDefault();
    if (!isValidFullName(fullName)) {
      status.setError(t(NAME_INVALID_KEY));
      return;
    }
    status.begin();
    try {
      const failureKey = await sendUserUpdate(user, {
        role,
        isActive,
        fullName,
      });
      if (failureKey !== undefined) {
        status.setError(t(failureKey));
        return;
      }
      onSuccess();
      onClose();
    } catch {
      status.setError(t(UPDATE_ERROR_KEY));
    } finally {
      status.finish();
    }
  };

  return (
    <UserDialogShell
      title={t("editUserTitle")}
      onClose={onClose}
      subtitle={<p className={DIALOG_MUTED_TEXT_CLASS}>{user.email}</p>}
      error={status.error}
      errorId={errorId}
    >
      <form
        noValidate
        onSubmit={(e) => {
          void handleSubmit(e);
        }}
        className="mt-4 space-y-4"
      >
        <FullNameField
          value={fullName}
          onChange={setFullName}
          errorId={nameErrorId}
        />

        <UserRoleSelect
          value={role}
          onChange={setRole}
          disabled={isLastActiveAdmin}
          describedBy={lockedBy}
        />

        <UserActiveField
          checked={isActive}
          onChange={setIsActive}
          disabled={isLastActiveAdmin}
          describedBy={lockedBy}
        />

        {isLastActiveAdmin && (
          <p id={lockHintId} className={DIALOG_MUTED_TEXT_CLASS}>
            {t(LAST_ACTIVE_ADMIN_LOCKED_KEY)}
          </p>
        )}

        <UserDialogActions
          onClose={onClose}
          isLoading={status.isLoading}
          label={t("save")}
          loadingLabel={t("saving")}
        />
      </form>
    </UserDialogShell>
  );
}
