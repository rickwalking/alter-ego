"use client";

import { type ChangeEvent } from "react";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonIcon } from "@/components/atoms/neon-icon";

const SEARCH_ICON_PATH = "M21 21l-6-6m2-5a7 7 0 1 1-14 0 7 7 0 0 1 14 0z";

export interface NeonSearchBarProps {
  value?: string;
  onChange?: (value: string) => void;
  placeholder?: string;
  className?: string;
}

export function NeonSearchBar({
  value,
  onChange,
  placeholder,
  className,
}: NeonSearchBarProps): React.ReactElement {
  const handleChange = (e: ChangeEvent<HTMLInputElement>): void => {
    onChange?.(e.target.value);
  };

  return (
    <div className={`relative ${className ?? ""}`}>
      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-dim pointer-events-none">
        <NeonIcon path={SEARCH_ICON_PATH} size={16} />
      </span>
      <NeonInput
        type="search"
        value={value}
        onChange={handleChange}
        placeholder={placeholder}
        className="pl-10"
      />
    </div>
  );
}
