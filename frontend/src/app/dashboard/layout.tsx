import { NeonAppShell } from "@/components/layout/neon-app-shell";

/** Dashboard shell: the shared neon app shell around every dashboard page. */
export default function DashboardLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.ReactElement {
  return <NeonAppShell>{children}</NeonAppShell>;
}
