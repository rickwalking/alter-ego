import { Header } from "@/components/layout";
import { BlogThemeEnforcer } from "@/components/layout/blog-theme-enforcer";

export default function BlogLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <>
      <BlogThemeEnforcer />
      <div className="dark min-h-full flex flex-col">
        <Header />
        <main className="flex-1">{children}</main>
      </div>
    </>
  );
}
