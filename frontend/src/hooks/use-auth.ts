"use client";

import { useState, useEffect, useCallback } from "react";

interface AuthUser {
  id: string;
  email: string;
  full_name: string;
  role: string;
}

interface UseAuthResult {
  user: AuthUser | null;
  isLoading: boolean;
  isAdmin: boolean;
  isEditor: boolean;
  logout: () => void;
}

export function useAuth(): UseAuthResult {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = useCallback(async () => {
    try {
      const response = await fetch("/api/auth/me", {
        credentials: "include",
      });

      if (response.ok) {
        const data = (await response.json()) as AuthUser;
        setUser(data);
      } else {
        setUser(null);
      }
    } catch {
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUser();
  }, [fetchUser]);

  const logout = useCallback(async () => {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch {
      // Ignore network errors; still redirect
    }
    setUser(null);
    window.location.href = "/login";
  }, []);

  return {
    user,
    isLoading,
    isAdmin: user?.role === "admin",
    isEditor: user?.role === "editor" || user?.role === "admin",
    logout,
  };
}
