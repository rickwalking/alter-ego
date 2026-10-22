"use client";

import { useEffect, useState } from "react";
import { useTranslations } from "next-intl";
import { useRouter } from "next/navigation";
import {
  AUTH_LOGIN_REDIRECT_PARAM,
  LOGIN_ERROR_INVALID_CREDENTIALS,
  LOGIN_ERROR_PARAM,
  LOGIN_ERROR_SESSION_EXPIRED,
  LOGIN_ERROR_TOO_MANY_ATTEMPTS,
} from "@/constants/auth";
import { sanitizeLoginRedirect } from "@/modules/identity";
import { responseErrorDetail } from "@/lib/response-error";

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

      if (response.status === HTTP_TOO_MANY_REQUESTS) {
        throw new Error(t("tooManyAttempts"));
      }
      if (!response.ok) {
        throw new Error(
          (await responseErrorDetail(response)) ?? t("loginError"),
        );
      }

      const params = new URLSearchParams(window.location.search);
      const redirectTo = sanitizeLoginRedirect(
        params.get(AUTH_LOGIN_REDIRECT_PARAM),
      );
      router.push(redirectTo);
      router.refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : t("loginError"));
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
