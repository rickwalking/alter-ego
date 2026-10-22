import { NeonButton } from "@/components/atoms/neon-button";
import { NEON_RED } from "@/constants/neon";

export interface NeonFormFooterProps {
  /** A save failure to announce, if any. */
  serverError: string | null;
  /** The "fix the highlighted fields" message, when the last submit was blocked. */
  invalidMessage: string | null;
  cancelLabel: string;
  submitLabel: string;
  saving: boolean;
  onCancel: () => void;
}

/** The end of a create/edit form: its announced errors, then Cancel and Submit. */
export function NeonFormFooter({
  serverError,
  invalidMessage,
  cancelLabel,
  submitLabel,
  saving,
  onCancel,
}: Readonly<NeonFormFooterProps>): React.ReactElement {
  return (
    <>
      {serverError && (
        <p role="alert" style={{ color: NEON_RED }} className="text-sm">
          {serverError}
        </p>
      )}
      {invalidMessage && (
        <p role="alert" style={{ color: NEON_RED }} className="text-sm">
          {invalidMessage}
        </p>
      )}
      <div className="flex justify-end gap-2">
        <NeonButton variant="ghost" onClick={onCancel}>
          {cancelLabel}
        </NeonButton>
        <NeonButton type="submit" variant="primary" loading={saving}>
          {submitLabel}
        </NeonButton>
      </div>
    </>
  );
}
