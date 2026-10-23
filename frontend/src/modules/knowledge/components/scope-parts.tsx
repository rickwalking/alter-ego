"use client";

import { useId } from "react";
import { Cog, Globe, Lock } from "lucide-react";
import { useTranslations } from "next-intl";

import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonLabel } from "@/components/atoms/neon-label";
import {
  DOCUMENT_SCOPE,
  SCOPE_FILTER_OPTIONS,
  type DocumentScopeChoice,
} from "@/constants/knowledge";
import { scopeChoiceOf } from "./document-scope";
import type {
  ScopeBadgeProps,
  ScopeFieldProps,
  ScopeFilterProps,
  ScopeSwitchProps,
} from "./types";

const SCOPE_CHOICES: readonly DocumentScopeChoice[] = [
  DOCUMENT_SCOPE.PERSONAL,
  DOCUMENT_SCOPE.PUBLIC,
];

const SYSTEM_SCOPE_LABEL = "system";

const SCOPE_ICONS = {
  [DOCUMENT_SCOPE.PERSONAL]: Lock,
  [DOCUMENT_SCOPE.PUBLIC]: Globe,
} as const;

/** "Pessoal", "Público" or "Sistema" for a document's scope. */
export function ScopeBadge({
  scope,
}: Readonly<ScopeBadgeProps>): React.ReactElement {
  const t = useTranslations("knowledge.scope");
  const choice = scopeChoiceOf(scope);
  const Icon = choice === null ? Cog : SCOPE_ICONS[choice];
  return (
    <NeonBadge
      variant="secondary"
      className="gap-1 text-xs"
      data-testid="document-scope"
    >
      <Icon className="h-3 w-3" aria-hidden="true" />
      {t(choice ?? SYSTEM_SCOPE_LABEL)}
    </NeonBadge>
  );
}

/** Personal / public radio choice of the upload and new-document forms. */
export function ScopeField({
  value,
  onChange,
  disabled = false,
}: Readonly<ScopeFieldProps>): React.ReactElement {
  const t = useTranslations("knowledge.scope");
  const name = useId();
  const hintId = `${name}-hint`;
  return (
    <fieldset className="space-y-2" aria-describedby={hintId}>
      <legend className="text-sm font-medium">{t("label")}</legend>
      <div className="flex flex-wrap gap-4">
        {SCOPE_CHOICES.map((choice) => (
          <NeonLabel
            key={choice}
            className="inline-flex items-center gap-2 font-normal"
          >
            <input
              type="radio"
              name={name}
              value={choice}
              checked={value === choice}
              onChange={() => onChange(choice)}
              disabled={disabled}
            />
            {t(choice)}
          </NeonLabel>
        ))}
      </div>
      <p id={hintId} className="text-xs text-[var(--color-muted-foreground)]">
        {t("hint")}
      </p>
    </fieldset>
  );
}

/** Todos / Pessoal / Público toggle above the document list. */
export function ScopeFilter({
  value,
  onChange,
}: Readonly<ScopeFilterProps>): React.ReactElement {
  const t = useTranslations("knowledge.scope");
  return (
    <div
      role="group"
      aria-label={t("filter")}
      className="inline-flex overflow-hidden rounded-md border border-[var(--color-border)]"
    >
      {SCOPE_FILTER_OPTIONS.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={value === option}
          onClick={() => onChange(option)}
          className="px-3 py-1.5 text-sm font-medium aria-pressed:bg-[var(--color-primary)]/15 aria-pressed:text-[var(--color-primary)] hover:bg-[var(--color-primary)]/10"
        >
          {t(option)}
        </button>
      ))}
    </div>
  );
}

/** "Tornar público" / "Tornar pessoal" on a document card. */
export function ScopeSwitch({
  scope,
  onSwitch,
  changing,
  failed,
}: Readonly<ScopeSwitchProps>): React.ReactElement {
  const t = useTranslations("knowledge.scope");
  const toPublic = scope !== DOCUMENT_SCOPE.PUBLIC;
  const label = toPublic ? t("makePublic") : t("makePersonal");
  return (
    <>
      {failed && (
        <p
          role="alert"
          className="mb-2 text-xs text-[var(--color-destructive)]"
        >
          {t("changeFailed")}
        </p>
      )}
      <button
        type="button"
        onClick={onSwitch}
        disabled={changing}
        className="mb-3 inline-flex items-center gap-1.5 rounded-md border border-[var(--color-border)] px-2.5 py-1 text-xs font-medium hover:bg-[var(--color-primary)]/10 disabled:opacity-50"
      >
        {changing ? t("changing") : label}
      </button>
    </>
  );
}
