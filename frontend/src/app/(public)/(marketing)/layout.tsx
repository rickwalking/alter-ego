import { PublicShellFrame } from "@/components/layout/public-header";

export default function MarketingLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): Promise<React.ReactElement> {
  return Promise.resolve(<PublicShellFrame>{children}</PublicShellFrame>);
}
