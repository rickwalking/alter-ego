"use client";

import { useCallback, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import {
  CreateTemplateSection,
  CreateThemeSection,
  CreateTopicSection,
} from "@/app/dashboard/create/create-form-sections";
import { CreateSidebar } from "@/app/dashboard/create/create-sidebar";
import { CreateModeSection } from "@/app/dashboard/create/workspace/create-mode-section";
import { CreatePovSection } from "@/app/dashboard/create/workspace/create-pov-section";
import { useDefaultPersona } from "@/app/dashboard/create/use-default-persona";
import { CreatePhotoSection } from "@/app/dashboard/create/workspace/create-photo-section";
import { usePovPhoto } from "@/app/dashboard/create/use-pov-photo";
import { CreateProgressSteps } from "@/app/dashboard/create/create-progress-steps";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import { buildCarouselCreateRequest } from "@/app/dashboard/create/helpers";
import { createErrorMessage } from "@/app/dashboard/create/create-error-message";
import {
  INITIAL_CREATE_FORM_STATE,
  isPovForm,
  showsFormatPicker,
  type CreateCarouselFormState,
} from "@/app/dashboard/create/types";
import { useCreateCarousel } from "@/modules/editorial";
import { usePaletteCatalog } from "@/modules/palette";
import { usePersonas } from "@/modules/persona";
import { buildThemeOptions } from "@/app/dashboard/create/theme-options";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { DEFAULT_IMAGE_PRESET } from "@/constants/create";

/** Any form change clears the error: an error about the previous input is stale. */
export default function CreateCarouselPage(): React.ReactElement {
  const router = useRouter();
  const locale = useLocale();
  const t = useTranslations("create");
  const createCarousel = useCreateCarousel();
  const { data: catalog } = usePaletteCatalog();
  const themeOptions = useMemo(
    () => buildThemeOptions(catalog, locale, t("themes.auto")),
    [catalog, locale, t],
  );
  const [form, setForm] = useState<CreateCarouselFormState>({
    ...INITIAL_CREATE_FORM_STATE,
    imagePreset: DEFAULT_IMAGE_PRESET,
  });
  const [error, setError] = useState<string | null>(null);

  const handleChange = useCallback(
    (patch: Partial<CreateCarouselFormState>): void => {
      setForm((prev) => ({ ...prev, ...patch }));
      setError(null);
    },
    [],
  );
  const { personas } = usePersonas();
  const selectPersona = useCallback(
    (personaId: string) => handleChange({ personaId }),
    [handleChange],
  );
  useDefaultPersona(personas, selectPersona);
  const selectPhoto = useCallback(
    (hookAssetId: string) => handleChange({ hookAssetId }),
    [handleChange],
  );
  const povPhoto = usePovPhoto(form.hookAssetId, selectPhoto);

  const handleSubmit = async (): Promise<void> => {
    setError(null);
    try {
      const payload = buildCarouselCreateRequest(form);
      const project = await createCarousel.mutateAsync(payload);
      router.push(DASHBOARD_ROUTES.CREATE_WORKSPACE(project.id));
    } catch (err) {
      setError(createErrorMessage(err, t));
    }
  };

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title={t("topBar.title")}
        breadcrumb={[{ label: t("topBar.newProject") }]}
      />

      <div className="p-7">
        <CreateProgressSteps
          activeStepId={CREATE_STEP_IDS.BRIEF}
          onStepChange={() => undefined}
        />
        <div className="grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,1fr)_360px]">
          <div className="flex flex-col gap-6">
            <CreateModeSection
              form={form}
              onChange={handleChange}
              personas={personas}
            />
            <CreateTopicSection form={form} onChange={handleChange} />
            {isPovForm(form) && (
              <CreatePovSection form={form} onChange={handleChange} />
            )}
            {isPovForm(form) && <CreatePhotoSection {...povPhoto.section} />}
            {showsFormatPicker(form) && (
              <CreateTemplateSection form={form} onChange={handleChange} />
            )}
            <CreateThemeSection
              form={form}
              onChange={handleChange}
              themeOptions={themeOptions}
            />
          </div>
          <CreateSidebar
            form={form}
            onSubmit={() => void handleSubmit()}
            isPending={createCarousel.isPending}
            error={error}
          />
        </div>
      </div>
    </div>
  );
}
