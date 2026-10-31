"use client";

import { useEffect, useRef } from "react";
import { useTranslations } from "next-intl";
import { NeonButton } from "@/components/atoms/neon-button";
import { DIALOG_BUTTON_CLASS } from "./user-dialog-parts";

interface DialogDoneButtonProps {
  onDone: () => void;
}

/**
 * The "Done" button that replaces a dialog's form once it succeeded. It takes
 * focus when it appears, because the submit button it replaces is gone.
 */
export function DialogDoneButton({ onDone }: Readonly<DialogDoneButtonProps>) {
  const t = useTranslations("admin");
  const ref = useRef<HTMLButtonElement>(null);
  useEffect(() => {
    ref.current?.focus();
  }, []);
  return (
    <div className="mt-6 flex justify-end">
      <NeonButton ref={ref} onClick={onDone} className={DIALOG_BUTTON_CLASS}>
        {t("done")}
      </NeonButton>
    </div>
  );
}
