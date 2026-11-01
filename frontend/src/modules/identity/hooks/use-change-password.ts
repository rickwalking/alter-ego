"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";

import { DEFAULT_LOGIN_REDIRECT } from "@/constants/auth";
import { authKeys } from "../queries";
import {
  passwordFormError,
  submitPasswordChange,
} from "../lib/change-password";
import type {
  ChangePasswordController,
  PasswordChangeErrorKey,
  PasswordChangeValues,
} from "../types";

const EMPTY_VALUES: PasswordChangeValues = {
  current: "",
  next: "",
  confirm: "",
};

/**
 * The change-password form: validates, sends, then refreshes the session.
 * After a forced change (`forced`) the user is sent on to the dashboard; a
 * normal change shows a success message and clears the form.
 */
export function useChangePassword(forced: boolean): ChangePasswordController {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [values, setValues] = useState<PasswordChangeValues>(EMPTY_VALUES);
  const [errorKey, setErrorKey] = useState<PasswordChangeErrorKey | null>(null);
  const [succeeded, setSucceeded] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const setField = (field: keyof PasswordChangeValues, value: string): void => {
    setValues((current) => ({ ...current, [field]: value }));
  };

  const finishSuccess = async (): Promise<void> => {
    await queryClient.invalidateQueries({ queryKey: authKeys.currentUser() });
    setValues(EMPTY_VALUES);
    setSucceeded(true);
    if (forced) {
      router.replace(DEFAULT_LOGIN_REDIRECT);
    }
  };

  const handleSubmit = async (event: React.SubmitEvent): Promise<void> => {
    event.preventDefault();
    setSucceeded(false);
    const invalid = passwordFormError(values);
    setErrorKey(invalid);
    if (invalid !== null) {
      return;
    }
    setIsLoading(true);
    const refused = await submitPasswordChange(values);
    setIsLoading(false);
    setErrorKey(refused);
    if (refused === null) {
      await finishSuccess();
    }
  };

  return { values, errorKey, succeeded, isLoading, setField, handleSubmit };
}
