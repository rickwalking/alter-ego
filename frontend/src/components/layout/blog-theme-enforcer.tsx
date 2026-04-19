"use client";

import { usePathname } from "next/navigation";
import { useEffect } from "react";

export function BlogThemeEnforcer() {
  const pathname = usePathname();

  useEffect(() => {
    const isBlog = pathname.startsWith("/blog");
    const root = document.documentElement;

    if (isBlog) {
      root.classList.add("dark");
      root.classList.remove("light");
    }

    return () => {
      if (isBlog) {
        root.classList.remove("dark");
      }
    };
  }, [pathname]);

  return null;
}
