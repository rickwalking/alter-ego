import { NEON_RED } from "@/constants/neon";

interface ActionErrorAlertProps {
  message: string | null;
}

/** A failed page action's message (`role="alert"`); renders nothing without one. */
export function ActionErrorAlert({
  message,
}: Readonly<ActionErrorAlertProps>): React.ReactElement | null {
  if (!message) return null;
  return (
    <p role="alert" className="text-center py-4" style={{ color: NEON_RED }}>
      {message}
    </p>
  );
}
