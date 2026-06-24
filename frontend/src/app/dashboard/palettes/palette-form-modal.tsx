"use client";

import { useTranslations } from "next-intl";
import { NeonBadge } from "@/components/atoms/neon-badge";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonModal } from "@/components/molecules/neon-modal";
import { NeonSelect } from "@/components/atoms/neon-select";
import {
  PALETTE_MODES,
  type CustomPalette,
  type PaletteCreateRequest,
} from "@/schemas/palette";
import { PaletteColorInput } from "./palette-color-input";
import { PaletteKeywordsField } from "./palette-keywords-field";
import { PaletteSwatch } from "./palette-swatch";
import { derivedImageStyleKey } from "./derived-image-style";
import { NAME_MAX, usePaletteForm } from "./use-palette-form";

interface PaletteFormModalProps {
  palette?: CustomPalette;
  onClose: () => void;
  onSave: (request: PaletteCreateRequest) => void;
  isPending: boolean;
  serverError?: string | null;
}

const COLOUR_FIELDS = ["primary", "accent", "background"] as const;

export function PaletteFormModal({
  palette,
  onClose,
  onSave,
  isPending,
  serverError,
}: PaletteFormModalProps): React.ReactElement {
  const t = useTranslations("palettes");
  const form = usePaletteForm(palette);
  const isEdit = palette !== undefined;

  const handleSubmit = (): void => {
    if (form.isValid) onSave(form.toRequest());
  };

  return (
    <NeonModal
      open
      onClose={onClose}
      title={isEdit ? t("form.editTitle") : t("form.createTitle")}
      footer={
        <div className="flex items-center justify-end gap-2">
          <NeonButton variant="ghost" onClick={onClose}>
            {t("action.cancel")}
          </NeonButton>
          <NeonButton
            variant="primary"
            loading={isPending}
            disabled={!form.isValid}
            onClick={handleSubmit}
          >
            {isEdit ? t("form.save") : t("form.create")}
          </NeonButton>
        </div>
      }
    >
      <div className="flex flex-col gap-4">
        <PaletteSwatch
          primary={form.state.primary}
          accent={form.state.accent}
          background={form.state.background}
          label={form.state.name || t("form.previewLabel")}
          height={56}
        />

        <div className="flex flex-col gap-1">
          <label htmlFor="palette-name" className="text-xs text-text-muted">
            {t("form.name")}
          </label>
          <NeonInput
            id="palette-name"
            value={form.state.name}
            maxLength={NAME_MAX}
            autoComplete="off"
            placeholder={t("form.namePlaceholder")}
            aria-invalid={form.errors.name !== undefined}
            onChange={(e) => form.setField("name", e.target.value)}
          />
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
          {COLOUR_FIELDS.map((field) => (
            <PaletteColorInput
              key={field}
              id={`palette-${field}`}
              label={t(`form.${field}`)}
              value={form.state[field]}
              onChange={(value) => form.setField(field, value)}
              invalid={form.errors[field] !== undefined}
              errorText={t("form.hexError")}
            />
          ))}
        </div>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <div className="flex flex-col gap-1">
            <label htmlFor="palette-mode" className="text-xs text-text-muted">
              {t("form.mode")}
            </label>
            <NeonSelect
              id="palette-mode"
              value={form.state.mode}
              onChange={(e) =>
                form.setField(
                  "mode",
                  e.target.value as (typeof PALETTE_MODES)[number],
                )
              }
            >
              {PALETTE_MODES.map((mode) => (
                <option key={mode} value={mode}>
                  {t(`mode.${mode}`)}
                </option>
              ))}
            </NeonSelect>
          </div>
          <div className="flex flex-col gap-1">
            <span className="text-xs text-text-muted">
              {t("form.imageStyle")}
            </span>
            <div className="flex h-10 items-center rounded-md border border-dashed border-white/10 px-3 text-sm text-text-muted">
              {t(derivedImageStyleKey(form.state.mode))}
            </div>
          </div>
        </div>

        <PaletteKeywordsField
          keywords={form.state.keywords}
          onAdd={form.addKeywords}
          onRemove={form.removeKeyword}
        />

        {serverError && (
          <NeonBadge variant="red" outline>
            {serverError}
          </NeonBadge>
        )}
      </div>
    </NeonModal>
  );
}
