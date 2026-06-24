"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { useLocale, useTranslations } from "next-intl";
import { NeonTopBar } from "@/components/organisms/neon-top-bar";
import {
  CreateTemplateSection,
  CreateThemeSection,
  CreateTopicSection,
} from "@/app/dashboard/create/create-form-sections";
import { CreateSidebar } from "@/app/dashboard/create/create-sidebar";
import { CreateProgressSteps } from "@/app/dashboard/create/create-progress-steps";
import { CREATE_STEP_IDS } from "@/app/dashboard/create/step-ids";
import { buildCarouselCreateRequest } from "@/app/dashboard/create/helpers";
import {
  INITIAL_CREATE_FORM_STATE,
  type CreateCarouselFormState,
} from "@/app/dashboard/create/types";
import { useCreateCarousel } from "@/modules/editorial";
import { usePaletteCatalog } from "@/modules/palette";
import { buildThemeOptions } from "@/app/dashboard/create/theme-options";
import { DASHBOARD_ROUTES } from "@/constants/dashboard-routes";
import { DEFAULT_IMAGE_PRESET } from "@/constants/create";

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

  const handleChange = (patch: Partial<CreateCarouselFormState>): void => {
    setForm((prev) => ({ ...prev, ...patch }));
  };

  const handleSubmit = async (): Promise<void> => {
    setError(null);
    try {
      const payload = buildCarouselCreateRequest(form);
      const project = await createCarousel.mutateAsync(payload);
      router.push(DASHBOARD_ROUTES.CREATE_WORKSPACE(project.id));
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Failed to create carousel",
      );
    }
  };

  return (
    <div
      className="flex-1 text-white relative"
      style={{ fontFamily: "Inter, system-ui, sans-serif" }}
    >
      <NeonTopBar
        title="Create Carousel"
        breadcrumb={[{ label: "new project" }]}
      />

      <div className="p-7">
        <CreateProgressSteps
          activeStepId={CREATE_STEP_IDS.BRIEF}
          onStepChange={() => undefined}
        />
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 360px",
            gap: "24px",
          }}
        >
          <div
            style={{ display: "flex", flexDirection: "column", gap: "24px" }}
          >
            <CreateTopicSection form={form} onChange={handleChange} />
            <CreateTemplateSection form={form} onChange={handleChange} />
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
