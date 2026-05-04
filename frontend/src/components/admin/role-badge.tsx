interface RoleBadgeProps {
  role: string;
}

export function RoleBadge({ role }: RoleBadgeProps) {
  const isAdmin = role === "admin";

  return (
    <span
      className={`inline-flex rounded-full px-2 text-xs font-semibold leading-5 ${
        isAdmin
          ? "bg-red-100 text-red-800"
          : "bg-blue-100 text-blue-800"
      }`}
    >
      {role}
    </span>
  );
}
