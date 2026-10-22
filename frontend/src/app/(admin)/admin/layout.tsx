import { AdminSidebar } from "@/components/admin/admin-sidebar";
import { SkipLink } from "@/components/atoms/skip-link";
import { MAIN_CONTENT_ID } from "@/constants/a11y";

export default function AdminLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <div className="flex min-h-screen bg-gray-50">
      <SkipLink />
      <AdminSidebar />
      <main id={MAIN_CONTENT_ID} tabIndex={-1} className="flex-1 p-8">
        {children}
      </main>
    </div>
  );
}
