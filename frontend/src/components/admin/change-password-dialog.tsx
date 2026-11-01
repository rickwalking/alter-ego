"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { adminErrorKey } from "@/lib/admin-user-errors";
import { responseErrorBody } from "@/lib/response-error";
import { DialogDoneButton } from "./dialog-done-button";
import {
  DIALOG_BUTTON_CLASS,
  DIALOG_MUTED_TEXT_CLASS,
  UserDialogActions,
  UserDialogShell,
  useDialogStatus,
  type UserDialogProps,
} from "./user-dialog-parts";

const RESET_ERROR_KEY = "resetError";

/** What the reset request ended in: the new password, or a key to translate. */
type ResetOutcome = { password: string } | { errorKey: string };

async function requestReset(userId: string): Promise<ResetOutcome> {
  const response = await fetch(`/api/admin/users/${userId}/reset-password`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) {
    const body = await responseErrorBody(response);
    return {
      errorKey: adminErrorKey(response.status, body) ?? RESET_ERROR_KEY,
    };
  }
  const data = (await response.json()) as { temp_password: string };
  return { password: data.temp_password };
}

interface TempPasswordProps {
  message: string;
  password: string;
}

/**
 * The temporary password, shown only in this dialog and never again, with a
 * copy button and the note that the user must change it at the next sign-in.
 */
function TempPassword({ message, password }: Readonly<TempPasswordProps>) {
  const t = useTranslations("admin");
  return (
    <>
      {message}
      <p className="mt-1">{t("resetMustChangeNote")}</p>
      <div className="mt-2 flex flex-wrap items-center gap-2">
        <code className="break-all rounded bg-bg-deep px-2 py-1 font-mono text-sm text-text-primary">
          {password}
        </code>
        <NeonButton
          variant="secondary"
          size="sm"
          onClick={() => {
            void navigator.clipboard.writeText(password);
          }}
          className={DIALOG_BUTTON_CLASS}
        >
          {t("copy")}
        </NeonButton>
      </div>
    </>
  );
}

export function ChangePasswordDialog({
  user,
  onClose,
  onSuccess,
}: Readonly<UserDialogProps>) {
  const t = useTranslations("admin");
  const [password, setPassword] = useState("");
  const status = useDialogStatus();

  const handleSubmit = async (e: React.SubmitEvent) => {
    e.preventDefault();
    status.begin();
    try {
      const outcome = await requestReset(user.id);
      if ("errorKey" in outcome) {
        status.setError(t(outcome.errorKey));
        return;
      }
      setPassword(outcome.password);
      status.setSuccess(t("resetSuccess"));
    } catch {
      status.setError(t(RESET_ERROR_KEY));
    } finally {
      status.finish();
    }
  };

  return (
    <UserDialogShell
      title={t("resetPasswordTitle")}
      onClose={onClose}
      subtitle={<p className={DIALOG_MUTED_TEXT_CLASS}>{user.email}</p>}
      error={status.error}
      success={
        status.success ? (
          <TempPassword message={status.success} password={password} />
        ) : undefined
      }
    >
      {!status.success && (
        <form
          onSubmit={(e) => {
            void handleSubmit(e);
          }}
          className="mt-4"
        >
          <p className={DIALOG_MUTED_TEXT_CLASS}>
            {t("resetPasswordDescription")}
          </p>
          <UserDialogActions
            onClose={onClose}
            isLoading={status.isLoading}
            label={t("reset")}
            loadingLabel={t("resetting")}
          />
        </form>
      )}

      {status.success && (
        <DialogDoneButton
          onDone={() => {
            onSuccess();
            onClose();
          }}
        />
      )}
    </UserDialogShell>
  );
}
