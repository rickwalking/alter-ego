import { useTranslations } from "next-intl";
import {
  CREATE_FORM_FIELDS,
  CAROUSEL_THEMES,
  DEFAULT_IMAGE_PRESET,
  IMAGE_PRESETS,
  THEME_LABEL_KEYS,
} from "@/constants/create";
import type { CarouselCreateRequest } from "@/schemas/carousel";

interface TopicFormProps {
  onSubmit: (data: CarouselCreateRequest) => void;
  isPending: boolean;
}

interface ThemeOption {
  value: string;
  labelKey: string;
}

const THEME_OPTIONS: ThemeOption[] = [
  { value: CAROUSEL_THEMES.AUTO, labelKey: THEME_LABEL_KEYS.auto },
  { value: CAROUSEL_THEMES.CYBERSECURITY, labelKey: THEME_LABEL_KEYS.cybersecurity },
  { value: CAROUSEL_THEMES.AI_COMPETITION, labelKey: THEME_LABEL_KEYS.ai_competition },
  { value: CAROUSEL_THEMES.DEVELOPER_SKILLS, labelKey: THEME_LABEL_KEYS.developer_skills },
  { value: CAROUSEL_THEMES.SOURCE_CODE, labelKey: THEME_LABEL_KEYS.source_code },
  { value: CAROUSEL_THEMES.SOCIAL_ENGINEERING, labelKey: THEME_LABEL_KEYS.social_engineering },
];

function presetFromValue(value: string): { model: string; style: string } {
  const preset = IMAGE_PRESETS.find((p) => p.value === value);
  if (preset) {
    return { model: preset.model, style: preset.style };
  }
  const fallback = IMAGE_PRESETS[0];
  return { model: fallback.model, style: fallback.style };
}

export function TopicForm({ onSubmit, isPending }: TopicFormProps) {
  const t = useTranslations("create");

  const handleSubmit = (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    const presetValue =
      (formData.get(CREATE_FORM_FIELDS.IMAGE_PRESET) as string) ||
      DEFAULT_IMAGE_PRESET;
    const { model, style } = presetFromValue(presetValue);
    onSubmit({
      topic: formData.get(CREATE_FORM_FIELDS.TOPIC) as string,
      audience: formData.get(CREATE_FORM_FIELDS.AUDIENCE) as string,
      niche: formData.get(CREATE_FORM_FIELDS.NICHE) as string,
      theme: (formData.get(CREATE_FORM_FIELDS.THEME) as string) || CAROUSEL_THEMES.AUTO,
      image_model: model as CarouselCreateRequest["image_model"],
      image_style: style as CarouselCreateRequest["image_style"],
    });
  };

  return (
    <form onSubmit={handleSubmit} className="mx-auto max-w-xl space-y-6">
      <div className="space-y-2">
        <label
          htmlFor={CREATE_FORM_FIELDS.TOPIC}
          className="block font-medium text-sm"
        >
          {t("form.topicLabel")}
        </label>
        <input
          id={CREATE_FORM_FIELDS.TOPIC}
          name={CREATE_FORM_FIELDS.TOPIC}
          type="text"
          required
          maxLength={500}
          placeholder={t("form.topicPlaceholder")}
          className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
        />
      </div>

      <div className="space-y-2">
        <label
          htmlFor={CREATE_FORM_FIELDS.AUDIENCE}
          className="block font-medium text-sm"
        >
          {t("form.audienceLabel")}
        </label>
        <input
          id={CREATE_FORM_FIELDS.AUDIENCE}
          name={CREATE_FORM_FIELDS.AUDIENCE}
          type="text"
          required
          maxLength={500}
          placeholder={t("form.audiencePlaceholder")}
          className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
        />
      </div>

      <div className="space-y-2">
        <label
          htmlFor={CREATE_FORM_FIELDS.NICHE}
          className="block font-medium text-sm"
        >
          {t("form.nicheLabel")}
        </label>
        <input
          id={CREATE_FORM_FIELDS.NICHE}
          name={CREATE_FORM_FIELDS.NICHE}
          type="text"
          required
          maxLength={200}
          placeholder={t("form.nichePlaceholder")}
          className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
        />
      </div>

      <div className="space-y-2">
        <label
          htmlFor={CREATE_FORM_FIELDS.THEME}
          className="block font-medium text-sm"
        >
          {t("form.themeLabel")}
        </label>
        <select
          id={CREATE_FORM_FIELDS.THEME}
          name={CREATE_FORM_FIELDS.THEME}
          className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
        >
          {THEME_OPTIONS.map((option) => (
            <option key={option.value} value={option.value}>
              {t(option.labelKey)}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-2">
        <label
          htmlFor={CREATE_FORM_FIELDS.IMAGE_PRESET}
          className="block font-medium text-sm"
        >
          {t("form.imagePresetLabel")}
        </label>
        <select
          id={CREATE_FORM_FIELDS.IMAGE_PRESET}
          name={CREATE_FORM_FIELDS.IMAGE_PRESET}
          defaultValue={DEFAULT_IMAGE_PRESET}
          className="w-full rounded-md border border-[var(--color-border)] bg-[var(--color-background)] px-3 py-2 text-sm focus:border-[var(--color-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--color-primary)]"
        >
          {IMAGE_PRESETS.map((option) => (
            <option key={option.value} value={option.value}>
              {t(option.labelKey)}
            </option>
          ))}
        </select>
        <p className="text-xs text-[var(--color-text-muted)]">
          {t("form.imagePresetHelp")}
        </p>
      </div>

      <button
        type="submit"
        disabled={isPending}
        className="w-full rounded-md bg-[var(--color-primary)] px-4 py-2 font-medium text-sm text-[var(--color-text)] transition-colors hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50"
      >
        {isPending ? t("form.submitting") : t("form.submit")}
      </button>
    </form>
  );
}
