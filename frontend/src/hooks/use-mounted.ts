import { useState, useEffect } from "react";

export function useMounted(): boolean {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    let cancelled = false;
    queueMicrotask(() => {
      if (!cancelled) {
        setMounted(true);
      }
    });
    return () => {
      cancelled = true;
    };
  }, []);

  return mounted;
}
