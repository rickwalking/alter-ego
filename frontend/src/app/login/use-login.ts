"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import {
  AUTH_LOGIN_REDIRECT_PARAM,
  LOGIN_ERROR_INVALID_CREDENTIALS,
  LOGIN_ERROR_PARAM,
  LOGIN_ERROR_SESSION_EXPIRED,
  LOGIN_ERROR_CODE_USER_INACTIVE,
  LOGIN_ERROR_TOO_MANY_ATTEMPTS,
} from "@/constants/auth";
import { sanitizeLoginRedirect } from "@/modules/identity";
import { errorBodyCode, responseErrorBody } from "@/lib/response-error";

export interface LoginController {
  email: string;
  password: string;
  error: string;
  isLoading: boolean;
  setEmail: (value: string) => void;
  setPassword: (value: string) => void;
  handleSubmit: (e: React.SubmitEvent) => Promise<void>;
}

const HTTP_TOO_MANY_REQUESTS = 429;
const LOGIN_ERROR_KEY = "loginError";

/**
 * The `auth` message key of a failed sign-in: rate-limited, a deactivated
 * account (its stable `code`), else invalid credentials. The API's English
 * `detail` is never shown.
 */
async function loginFailureKey(response: Response): Promise<string> {
  if (response.status === HTTP_TOO_MANY_REQUESTS) {
    return "tooManyAttempts";
  }
  const code = errorBodyCode(await responseErrorBody(response));
  return code === LOGIN_ERROR_CODE_USER_INACTIVE
    ? "accountDeactivated"
    : LOGIN_ERROR_KEY;
}

function useSessionExpiredNotice(setError: (message: string) => void) {
  const t = useTranslations("auth");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const notice = params.get(LOGIN_ERROR_PARAM);
    if (notice === LOGIN_ERROR_SESSION_EXPIRED) {
      setError(t("sessionExpired"));
    }
    if (notice === LOGIN_ERROR_INVALID_CREDENTIALS) {
      setError(t("loginError"));
    }
    if (notice === LOGIN_ERROR_TOO_MANY_ATTEMPTS) {
      setError(t("tooManyAttempts"));
    }
  }, [setError, t]);
}

export function useLogin(): LoginController {
  const t = useTranslations("auth");
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  useSessionExpiredNotice(setError);

  const handleSubmit = async (e: React.SubmitEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      const response = await fetch("/api/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ email, password }),
      });

      if (!response.ok) {
        setError(t(await loginFailureKey(response)));
        return;
      }

      const params = new URLSearchParams(window.location.search);
      const redirectTo = sanitizeLoginRedirect(
        params.get(AUTH_LOGIN_REDIRECT_PARAM),
      );
      router.push(redirectTo);
      router.refresh();
    } catch {
      setError(t(LOGIN_ERROR_KEY));
    } finally {
      setIsLoading(false);
    }
  };

  return {
    email,
    password,
    error,
    isLoading,
    setEmail,
    setPassword,
    handleSubmit,
  };
}
