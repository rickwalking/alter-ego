import type { ReactNode, RefObject } from "react";
import { NeonInput } from "@/components/atoms/neon-input";
import { NeonTextarea } from "@/components/atoms/neon-textarea";
import {
  NeonLabelledField,
  invalidProps,
} from "@/components/molecules/neon-labelled-field";

export interface NeonEntityFormProps {
  formRef: RefObject<HTMLFormElement | null>;
  /** Prefix of the heading id (`<idPrefix>-form-title`). */
  idPrefix: string;
  title: string;
  onSubmit: (event: React.SubmitEvent<HTMLFormElement>) => Promise<void>;
  children: ReactNode;
}

/** A dashboard create/edit form: labelled by its heading, browser validation off. */
export function NeonEntityForm({
  formRef,
  idPrefix,
  title,
  onSubmit,
  children,
}: Readonly<NeonEntityFormProps>): React.ReactElement {
  const titleId = `${idPrefix}-form-title`;
  return (
    <form
      ref={formRef}
      noValidate
      aria-labelledby={titleId}
      className="flex max-w-3xl flex-col gap-5"
      onSubmit={(e) => void onSubmit(e)}
    >
      <h2 id={titleId} className="text-lg font-bold">
        {title}
      </h2>
      {children}
    </form>
  );
}

export interface NeonNameFieldProps {
  id: string;
  label: string;
  placeholder: string;
  maxLength: number;
  value: string;
  error: string | undefined;
  onChange: (value: string) => void;
}

/** The required name input of an entity form, with its error wiring. */
export function NeonNameField({
  id,
  label,
  placeholder,
  maxLength,
  value,
  error,
  onChange,
}: Readonly<NeonNameFieldProps>): React.ReactElement {
  return (
    <NeonLabelledField id={id} label={label} error={error}>
      <NeonInput
        id={id}
        value={value}
        maxLength={maxLength}
        autoComplete="off"
        placeholder={placeholder}
        {...invalidProps(id, error)}
        onChange={(e) => onChange(e.target.value)}
      />
    </NeonLabelledField>
  );
}

export interface NeonDescriptionFieldProps {
  id: string;
  label: string;
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
}

/** The optional free-text description of an entity form. */
export function NeonDescriptionField({
  id,
  label,
  placeholder,
  value,
  onChange,
}: Readonly<NeonDescriptionFieldProps>): React.ReactElement {
  return (
    <NeonLabelledField id={id} label={label}>
      <NeonTextarea
        id={id}
        value={value}
        placeholder={placeholder}
        onChange={(e) => onChange(e.target.value)}
      />
    </NeonLabelledField>
  );
}
