import { NeonAppShell } from "@/components/layout/neon-app-shell";

/**
 * Admin shell: the same neon app shell as the dashboard (sidebar drawer on a
 * phone, EN/PT switch, dark theme). The top padding below lg keeps the page
 * heading clear of the fixed menu button.
 */
export default function AdminLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <NeonAppShell>
      <div className="w-full px-4 pb-8 pt-16 sm:px-6 lg:p-8">{children}</div>
    </NeonAppShell>
  );
}
