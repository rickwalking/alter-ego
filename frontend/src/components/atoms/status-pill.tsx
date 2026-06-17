export interface StatusPillProps {
  /** Text shown in the pill (e.g. the status label). */
  label: string;
  /** Foreground colour for the text + dot. */
  color: string;
  /** Dimmed background colour behind the pill. */
  background: string;
}

/**
 * Small status pill with a leading dot (AE-0154). Shared by the persona and
 * rubric status badges, which differ only in their colour palette — the caller
 * resolves `color`/`background` from its own palette and passes them in.
 */
export function StatusPill({
  label,
  color,
  background,
}: StatusPillProps): React.ReactElement {
  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 10px",
        borderRadius: 20,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.5px",
        textTransform: "uppercase",
        color,
        background,
      }}
    >
      <span
        style={{
          width: 5,
          height: 5,
          borderRadius: "50%",
          background: color,
          display: "inline-block",
        }}
      />
      {label}
    </span>
  );
}
