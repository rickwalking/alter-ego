"use client";

import { useState } from "react";
import { useLocale, useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { NeonSpinner } from "@/components/atoms/neon-spinner";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import { NEON_RED } from "@/constants/neon";
import { ApiError } from "@/lib/api-client";
import {
  useArchivePalette,
  useCreatePalette,
  usePaletteCatalog,
  useUpdatePalette,
} from "@/modules/palette";
import type {
  CustomPalette,
  PaletteCreateRequest,
  RootPalette,
} from "@/schemas/palette";
import { PaletteCard } from "./palette-card";
import { PaletteFormModal } from "./palette-form-modal";
import { PalettesEmptyState } from "./palettes-empty-state";

const PAGE_FONT_FAMILY = "Inter, system-ui, sans-serif";
// Responsive auto-fill grid; 200px min so cards fit a 360px phone.
const GRID_CLASS = "grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-4";

type FormTarget = { kind: "create" } | { kind: "edit"; palette: CustomPalette };

function rootLabel(root: RootPalette, locale: string): string {
  return locale === "pt" ? root.label_pt : root.label_en;
}

/** Map a save failure to its i18n key (409 duplicate / 422 invalid / generic). */
function errorKey(err: unknown): string {
  if (err instanceof ApiError && err.status === 409) return "error.duplicate";
  if (err instanceof ApiError && err.status === 422) return "error.invalid";
  return "error.generic";
}

export default function PalettesPage(): React.ReactElement {
  const t = useTranslations("palettes");
  const locale = useLocale();
  const { data, isLoading, error } = usePaletteCatalog();
  const createPalette = useCreatePalette();
  const updatePalette = useUpdatePalette();
  const archivePalette = useArchivePalette();
  const [target, setTarget] = useState<FormTarget | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  const closeForm = (): void => {
    setTarget(null);
    setServerError(null);
  };

  const handleSave = (request: PaletteCreateRequest): void => {
    setServerError(null);
    const onError = (err: unknown): void => setServerError(t(errorKey(err)));
    if (target?.kind === "edit") {
      updatePalette.mutate(
        { id: target.palette.id, data: request },
        { onSuccess: closeForm, onError },
      );
      return;
    }
    createPalette.mutate(request, { onSuccess: closeForm, onError });
  };

  const isSaving = createPalette.isPending || updatePalette.isPending;

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: PAGE_FONT_FAMILY }}
    >
      <NeonTopBar
        title={t("title")}
        breadcrumb={[{ label: t("breadcrumb") }]}
        actions={
          <NeonButton
            variant="primary"
            size="sm"
            onClick={() => setTarget({ kind: "create" })}
          >
            {t("action.new")}
          </NeonButton>
        }
      />

      <div className="page-content px-4 py-6 md:px-8">
        {isLoading && (
          <div className="flex justify-center py-12">
            <NeonSpinner size="lg" />
          </div>
        )}
        {error && !isLoading && (
          <p className="text-center py-8" style={{ color: NEON_RED }}>
            {t("error.load")}
          </p>
        )}

        {!isLoading && !error && data && (
          <div className="flex flex-col gap-8">
            <section className="flex flex-col gap-3">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                {t("section.custom")}
              </h2>
              {data.custom.length === 0 ? (
                <PalettesEmptyState
                  onCreate={() => setTarget({ kind: "create" })}
                />
              ) : (
                <div className={GRID_CLASS}>
                  {data.custom.map((palette) => (
                    <PaletteCard
                      key={palette.id}
                      name={palette.name}
                      primary={palette.primary}
                      accent={palette.accent}
                      background={palette.background}
                      mode={palette.mode}
                      keywords={palette.keywords}
                      isRoot={false}
                      onEdit={() => setTarget({ kind: "edit", palette })}
                      onArchive={() => archivePalette.mutate(palette.id)}
                      isArchiving={archivePalette.isPending}
                    />
                  ))}
                </div>
              )}
            </section>

            <section className="flex flex-col gap-3">
              <h2 className="text-xs font-semibold uppercase tracking-wide text-text-muted">
                {t("section.roots")}
              </h2>
              <div className={GRID_CLASS}>
                {data.roots.map((root) => (
                  <PaletteCard
                    key={root.key}
                    name={rootLabel(root, locale)}
                    primary={root.primary}
                    accent={root.accent}
                    background={root.background}
                    mode={root.mode}
                    isRoot
                  />
                ))}
              </div>
            </section>
          </div>
        )}
      </div>

      {target && (
        <PaletteFormModal
          key={target.kind === "edit" ? target.palette.id : "create"}
          palette={target.kind === "edit" ? target.palette : undefined}
          onClose={closeForm}
          onSave={handleSave}
          isPending={isSaving}
          serverError={serverError}
        />
      )}
    </div>
  );
}
