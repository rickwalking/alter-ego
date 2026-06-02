"use client";

import { createContext, useContext, useState, type ReactNode } from "react";
import { cn } from "@/lib/utils";
import { NeonBadge } from "@/components/atoms/neon-badge";

interface NeonTabContextValue {
  activeTab: string;
  setActiveTab: (id: string) => void;
}

const NeonTabContext = createContext<NeonTabContextValue | null>(null);

function useNeonTab(): NeonTabContextValue {
  const ctx = useContext(NeonTabContext);
  if (!ctx) {
    throw new Error("NeonTab components must be used within NeonTabs");
  }
  return ctx;
}

export interface NeonTabsProps {
  defaultValue: string;
  children: ReactNode;
  className?: string;
}

export function NeonTabs({
  defaultValue,
  children,
  className,
}: NeonTabsProps): React.ReactElement {
  const [activeTab, setActiveTab] = useState(defaultValue);

  return (
    <NeonTabContext.Provider value={{ activeTab, setActiveTab }}>
      <div className={className}>{children}</div>
    </NeonTabContext.Provider>
  );
}

export interface NeonTabListProps {
  children: ReactNode;
}

export function NeonTabList({
  children,
}: NeonTabListProps): React.ReactElement {
  return (
    <div
      className="flex gap-1 border-b border-[var(--color-neon-card-border)] mb-4"
      role="tablist"
    >
      {children}
    </div>
  );
}

export interface NeonTabTriggerProps {
  value: string;
  children: ReactNode;
  badge?: string;
}

export function NeonTabTrigger({
  value,
  children,
  badge,
}: NeonTabTriggerProps): React.ReactElement {
  const { activeTab, setActiveTab } = useNeonTab();
  const isActive = activeTab === value;

  return (
    <button
      type="button"
      role="tab"
      aria-selected={isActive}
      className={cn(
        "px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px",
        isActive
          ? "border-neon-cyan text-neon-cyan"
          : "border-transparent text-text-muted hover:text-text-primary",
      )}
      onClick={() => setActiveTab(value)}
    >
      {children}
      {badge && (
        <NeonBadge variant="magenta" size="sm" className="ml-2">
          {badge}
        </NeonBadge>
      )}
    </button>
  );
}

export interface NeonTabPanelProps {
  value: string;
  children: ReactNode;
}

export function NeonTabPanel({
  value,
  children,
}: NeonTabPanelProps): React.ReactElement | null {
  const { activeTab } = useNeonTab();

  if (activeTab !== value) {
    return null;
  }

  return (
    <div role="tabpanel" className="pt-2">
      {children}
    </div>
  );
}
