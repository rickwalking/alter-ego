import { PublicShellFrame } from "@/components/layout/public-header";

export default async function MarketingLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): Promise<React.ReactElement> {
  return <PublicShellFrame>{children}</PublicShellFrame>;
}
