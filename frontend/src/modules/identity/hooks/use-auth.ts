"use client";

import { useCallback } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";

import { PUBLIC_ROUTE_PATHS } from "@/constants/public-routes";
import { currentUserOptions, postLogout } from "../queries";
import type { UseAuthResult } from "../types";

const ROLE_ADMIN = "admin";
const ROLE_EDITOR = "editor";

export function useAuth(): UseAuthResult {
  const { data: user = null, isPending } = useQuery(currentUserOptions());

  const logoutMutation = useMutation({
    // Backend logout is best-effort; ignore network errors and still redirect.
    mutationFn: () => postLogout().catch(() => undefined),
    onSettled: () => {
      window.location.href = PUBLIC_ROUTE_PATHS.LOGIN;
    },
  });

  const logout = useCallback(() => {
    logoutMutation.mutate();
  }, [logoutMutation]);

  return {
    user,
    isLoading: isPending,
    isAdmin: user?.role === ROLE_ADMIN,
    isEditor: user?.role === ROLE_EDITOR || user?.role === ROLE_ADMIN,
    logout,
  };
}
