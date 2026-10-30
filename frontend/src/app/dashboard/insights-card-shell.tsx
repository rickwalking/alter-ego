"use client";

import type { ReactNode } from "react";
import { NeonCard } from "@/components/molecules/neon-card";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NEON_RED, TEXT, TEXT_MUTED } from "@/constants/neon";

/**
 * The shared chrome of the Instagram insights surfaces (the dashboard card
 * and the analytics-page section): title, subtitle, loading and error
 * states around the fetched body.
 */
export function InsightsCardShell({
  title,
  subtitle,
  loadFailed,
  isLoading,
  isError,
  children,
}: Readonly<{
  title: string;
  subtitle: string;
  loadFailed: string;
  isLoading: boolean;
  isError: boolean;
  children: ReactNode;
}>): React.ReactElement {
  return (
    <NeonCard padding="md">
      <h2
        className="font-extrabold tracking-tight mb-1"
        style={{ fontSize: 18, color: TEXT }}
      >
        {title}
      </h2>
      <p className="text-xs mb-4" style={{ color: TEXT_MUTED }}>
        {subtitle}
      </p>
      {isLoading && (
        <div className="flex justify-center py-6">
          <NeonSpinner size="md" />
        </div>
      )}
      {isError && (
        <p className="text-sm" style={{ color: NEON_RED }}>
          {loadFailed}
        </p>
      )}
      {children}
    </NeonCard>
  );
}
