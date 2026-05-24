"use client";

import { Analytics } from "@vercel/analytics/react";
import { SpeedInsights } from "@vercel/speed-insights/next";

function isVercel(): boolean {
  if (typeof window === "undefined") return false;
  return (
    window.location.hostname !== "localhost" &&
    window.location.hostname !== "127.0.0.1" &&
    !!process.env.NEXT_PUBLIC_VERCEL_DEPLOYMENT
  );
}

export function VercelInsights() {
  if (!isVercel()) {
    return null;
  }

  return (
    <>
      <Analytics />
      <SpeedInsights />
    </>
  );
}
