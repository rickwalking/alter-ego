"use client";

import {
  createContext,
  useContext,
  useState,
  type ReactNode,
  useRef,
  useEffect,
} from "react";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonCard } from "@/components/molecules/neon-card";

interface NeonDropdownContextValue {
  open: boolean;
  setOpen: (open: boolean) => void;
}

const NeonDropdownContext = createContext<NeonDropdownContextValue | null>(
  null,
);

function useNeonDropdown(): NeonDropdownContextValue {
  const ctx = useContext(NeonDropdownContext);
  if (!ctx) {
    throw new Error("NeonDropdown components must be used within NeonDropdown");
  }
  return ctx;
}

export interface NeonDropdownProps {
  children: ReactNode;
}

export function NeonDropdown({ children }: NeonDropdownProps): React.ReactElement {
  const [open, setOpen] = useState(false);

  return (
    <NeonDropdownContext.Provider value={{ open, setOpen }}>
      <div className="relative inline-block">{children}</div>
    </NeonDropdownContext.Provider>
  );
}

export interface NeonDropdownTriggerProps {
  children: ReactNode;
}

export function NeonDropdownTrigger({
  children,
}: NeonDropdownTriggerProps): React.ReactElement {
  const { open, setOpen } = useNeonDropdown();

  return (
    <NeonButton variant="ghost" onClick={() => setOpen(!open)} aria-expanded={open}>
      {children}
    </NeonButton>
  );
}

export interface NeonDropdownContentProps {
  children: ReactNode;
  align?: "start" | "end";
}

export function NeonDropdownContent({
  children,
  align = "end",
}: NeonDropdownContentProps): React.ReactElement | null {
  const { open, setOpen } = useNeonDropdown();
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) {
      return;
    }
    const handleClickOutside = (e: MouseEvent): void => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [open, setOpen]);

  if (!open) {
    return null;
  }

  return (
    <div
      ref={ref}
      className={`absolute top-full mt-2 z-50 min-w-[160px] ${
        align === "end" ? "right-0" : "left-0"
      }`}
    >
      <NeonCard padding="sm">{children}</NeonCard>
    </div>
  );
}

export interface NeonDropdownItemProps {
  children: ReactNode;
  onClick?: () => void;
}

export function NeonDropdownItem({
  children,
  onClick,
}: NeonDropdownItemProps): React.ReactElement {
  const { setOpen } = useNeonDropdown();

  return (
    <button
      type="button"
      className="w-full text-left px-3 py-2 text-sm text-text-primary hover:bg-neon-cyan-dim rounded transition-colors"
      onClick={() => {
        onClick?.();
        setOpen(false);
      }}
    >
      {children}
    </button>
  );
}
