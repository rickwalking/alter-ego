interface RoleBadgeProps {
  role: string;
}

export function RoleBadge({ role }: RoleBadgeProps) {
  const isAdmin = role === "admin";

  return (
    <span
      className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
        isAdmin
          ? "bg-destructive/20 text-destructive"
          : "bg-info/20 text-info-foreground"
      }`}
    >
      {role}
    </span>
  );
}
