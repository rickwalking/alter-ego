import { NeonGridBackground, NeonScanlineOverlay } from "@/components/organisms";
import { BG_DEEP } from "@/constants/neon";

export default function PublicLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>): React.ReactElement {
  return (
    <div className="min-h-full flex flex-col" style={{ background: BG_DEEP }}>
      <NeonGridBackground />
      <NeonScanlineOverlay />
      {children}
    </div>
  );
}
